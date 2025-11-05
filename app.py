"""
Flask Application with Anime Recommendation System
Includes automatic scheduler to train model daily at 2:30 AM
"""

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pathlib import Path
import threading
import sys
import os
import time

# Add src/ to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.recommendation_system import RecommendationSystem

# APScheduler for automatic tasks
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


# Flask configuration
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
CORS(app)
app.config["DEBUG"] = False
app.config["PORT"] = 5000

# Path configuration
DATA_DIR = Path(__file__).resolve().parent / 'data'
ANIME_CSV = DATA_DIR / 'anime.csv'
RATING_CSV = DATA_DIR / 'cleaned_data.csv'

print("="*70)
print("INITIALIZING RECOMMENDATION SYSTEM")
print("="*70)
print(f"\nSearching for files:")
print(f"  - {ANIME_CSV}")
print(f"  - {RATING_CSV}")

# Global variable for recommendation system
rec_system = None
training_in_progress = False
last_model_check = None


def initialize_system():
    """
    Initialize the recommendation system
    """
    global rec_system
    try:
        rec_system = RecommendationSystem(
            anime_csv_path=ANIME_CSV,
            rating_csv_path=RATING_CSV
        )
        print("\nSystem loaded correctly!")
        return True
    except FileNotFoundError as e:
        print(f"\nERROR: {str(e)}")
        print("\n" + "="*70)
        return False
    except Exception as e:
        print(f"\nUNEXPECTED ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\n" + "="*70)
        return False


def check_for_new_models():
    """
    Check if new models are available and load them automatically
    Runs every 30 seconds to detect manually trained models
    """
    global rec_system, last_model_check
    
    if rec_system is None or training_in_progress:
        return
    
    try:
        latest_version = rec_system._get_latest_version()
        
        if latest_version > rec_system.current_model_version:
            print(f"\nNEW MODEL DETECTED: v{latest_version}")
            print(f"   Current model: v{rec_system.current_model_version}")
            print(f"   Reloading automatically...")
            
            if rec_system.reload_model():
                print(f"Model v{latest_version} loaded successfully!")
                last_model_check = time.time()
            else:
                print(f"Could not load model v{latest_version}")
    except Exception as e:
        pass


def check_and_retrain():
    """
    Check if data has changed and retrain model if necessary
    This function runs daily at 2:30 AM
    """
    global rec_system, training_in_progress
    
    print("\n" + "="*70)
    print("DAILY AUTOMATIC CHECK - 2:30 AM")
    print("="*70)
    
    if rec_system is None:
        print("System not initialized. Skipping check.")
        return
    
    if training_in_progress:
        print("Training already in progress. Skipping check.")
        return
    
    # Check if data has changed
    if not rec_system.has_data_changed():
        print("Data hasn't changed. No retraining needed.")
        print("="*70)
        return
    
    print("NEW DATA DETECTED!")
    print("Starting model training in background...")
    print("="*70)
    
    # Train in separate thread to avoid blocking
    training_thread = threading.Thread(target=train_model_background)
    training_thread.daemon = True
    training_thread.start()


def train_model_background():
    """
    Train model in background without blocking the application
    Once finished, reload the new model automatically
    """
    global rec_system, training_in_progress
    
    training_in_progress = True
    
    try:
        print("\nBACKGROUND TRAINING STARTED")
        print("This may take a few minutes...")
        
        # Train model (this takes time)
        rec_system.train_model(save=True)
        
        print("\nModel trained! Reloading...")
        
        # Reload new model
        if rec_system.reload_model():
            print("New model loaded correctly!")
            print(f"Now using version v{rec_system.current_model_version}")
        else:
            print("Could not reload new model")
        
    except Exception as e:
        print(f"Error during training: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        training_in_progress = False
        print("="*70)


def setup_scheduler():
    """
    Configure scheduler for:
    1. Run check_and_retrain daily at 2:30 AM
    2. Check for new models every 30 seconds
    """
    scheduler = BackgroundScheduler()
    
    # Trigger 1: Daily check at 2:30 AM
    trigger_daily = CronTrigger(hour=2, minute=30)
    
    scheduler.add_job(
        func=check_and_retrain,
        trigger=trigger_daily,
        id='daily_model_check',
        name='Daily model check',
        replace_existing=True
    )
    
    # Trigger 2: Check for new models every 30 seconds
    scheduler.add_job(
        func=check_for_new_models,
        trigger='interval',
        seconds=30,
        id='model_watcher',
        name='New model watcher',
        replace_existing=True
    )
    
    scheduler.start()
    
    print("\nSCHEDULER CONFIGURED")
    print(f"   Automatic check: daily at 2:30 AM")
    print(f"   Model watcher: every 30 seconds")
    print(f"   Will automatically reload new models")
    
    return scheduler


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/', methods=['GET'])
def home():
    """Main page"""
    return render_template('index.html')


@app.route('/api/model-info', methods=['GET'])
def get_model_info():
    """
    Endpoint to get information about current model
    GET /api/model-info
    
    Returns:
        {
            "version": 3,
            "loaded_at": "2024-10-28T12:30:45",
            "num_animes": 12294,
            "num_users": 73516,
            "num_ratings": 2156789,
            "data_changed": false,
            "training_in_progress": false
        }
    """
    if rec_system is None:
        return jsonify({
            "error": "System not initialized"
        }), 503
    
    try:
        model_info = rec_system.get_model_info()
        model_info['training_in_progress'] = training_in_progress
        return jsonify(model_info)
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route('/api/recommendations', methods=['POST'])
def get_recommendations():
    """
    Endpoint to get recommendations based on an anime
    POST: { "anime": "Death Note", "rating": 4.5 }
    """
    if rec_system is None:
        return jsonify({
            "error": "System is not initialized. "
                     "Run 'python scripts/train_model.py' first."
        }), 503
    
    try:
        data = request.get_json()
        anime_name = data.get('anime')
        rating = data.get('rating', 5)
        
        if not anime_name:
            return jsonify({
                "error": "Parameter 'anime' is required"
            }), 400
        
        # Search for matching animes
        matching_animes = rec_system.search_anime_exact(anime_name)
        
        # If multiple matches, return them for selection
        if len(matching_animes) > 1:
            return jsonify({
                "status": "multiple_matches",
                "message": f"Found {len(matching_animes)} animes with this name",
                "matches": matching_animes[:10],
                "query": anime_name
            }), 300
        
        # If only one match or none
        if len(matching_animes) == 1:
            anime_name = matching_animes[0]['name']
        
        # Get adjusted recommendations based on rating
        recommendations, exact_anime_name = rec_system.get_recommendations_adjusted(
            anime_name=anime_name,
            user_rating=rating,
            num_recommendations=6
        )
        
        if recommendations is None:
            return jsonify({
                "error": f"Anime '{anime_name}' not found. "
                         "Try a more specific search."
            }), 404
        
        return jsonify({
            "anime": exact_anime_name,  # Return exact anime name used
            "user_rating": rating,
            "recommendations": recommendations
        })
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": f"Internal server error: {str(e)}"
        }), 500


@app.route('/api/recommendations-multiple', methods=['POST'])
def get_recommendations_multiple():
    """
    Endpoint to get recommendations based on multiple animes
    POST: { "ratings": { "Death Note": 5, "Code Geass": 4.5 } }
    """
    if rec_system is None:
        return jsonify({
            "error": "System not initialized"
        }), 503
    
    try:
        data = request.get_json()
        ratings = data.get('ratings')
        
        if not ratings or not isinstance(ratings, dict):
            return jsonify({
                "error": "Parameter 'ratings' is required and must be a dictionary"
            }), 400
        
        recommendations = rec_system.get_recommendations_for_user(
            user_ratings_dict=ratings,
            num_recommendations=10
        )
        
        return jsonify({
            "user_ratings": ratings,
            "recommendations": recommendations
        })
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": f"Internal error: {str(e)}"
        }), 500


@app.route('/api/animes', methods=['GET'])
def get_animes():
    """Return list of all available animes"""
    if rec_system is None:
        return jsonify({"error": "System not initialized"}), 503
    
    try:
        animes = rec_system.get_all_animes()
        return jsonify({
            "animes": animes,
            "count": len(animes)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/search', methods=['GET'])
def search_anime():
    """Search animes by name"""
    if rec_system is None:
        return jsonify({"error": "System not initialized"}), 503
    
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify({
                "error": "Parameter 'q' is required"
            }), 400
            
        results = rec_system.search_anime(query)
        return jsonify({
            "results": results,
            "count": len(results)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/models', methods=['GET'])
def list_models():
    """List all available models"""
    if rec_system is None:
        return jsonify({"error": "System not initialized"}), 503
    
    try:
        models = rec_system.list_available_models()
        return jsonify({
            "models": models,
            "count": len(models)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/train', methods=['POST'])
def manual_train():
    """
    Endpoint to force manual model training
    POST /api/train
    """
    global training_in_progress
    
    if rec_system is None:
        return jsonify({"error": "System not initialized"}), 503
    
    if training_in_progress:
        return jsonify({
            "error": "Training already in progress. Please wait for it to finish."
        }), 409
    
    # Start training in background
    training_thread = threading.Thread(target=train_model_background)
    training_thread.daemon = True
    training_thread.start()
    
    return jsonify({
        "message": "Training started in background",
        "training_in_progress": True
    })


# ============================================================================
# INITIALIZATION AND EXECUTION
# ============================================================================

if __name__ == '__main__':
    # Initialize system
    if initialize_system():
        print("\n" + "="*70)
        print("FLASK SERVER STARTED SUCCESSFULLY")
        print("="*70)
        print(f"System loaded with:")
        print(f"  - {len(rec_system.animes_dict)} animes")
        print(f"  - {len(rec_system.users_dict)} users")
        print(f"  - Model v{rec_system.current_model_version}")
        
        # Configure automatic scheduler
        scheduler = setup_scheduler()
        
        try:
            # Host must be '0.0.0.0' to accept external connections
            # Cannot be a URL like 'https://recomanador.hermes.cat'
            host = '0.0.0.0'  # This allows access from any IP
            port = int(os.environ.get('PORT', 5000))
            
            print(f"\nServer started!")
            print(f"  - Local: http://localhost:{port}")
            print(f"  - Network: http://0.0.0.0:{port}")
            print(f"  - Production: https://recomanador.hermes.cat")
            print("="*70 + "\n")
            
            app.run(debug=False, host=host, port=port, use_reloader=False)
            
        except (KeyboardInterrupt, SystemExit):
            # Stop scheduler when closing app
            scheduler.shutdown()
            print("\nScheduler stopped. Goodbye!")
    else:
        print("\n" + "="*70)
        print("CANNOT START SERVER")
        print("="*70)
        print("\nTo fix:")
        print("  1. Run: python scripts/train_model.py")
        print("  2. Or run: ./scripts/train_auto.sh")
        print("  3. Then run again: python app.py")
        print("="*70 + "\n")
