"""
Aplicació Flask amb Sistema de Recomanacions d'Animes
Inclou scheduler automàtic per entrenar el model cada dia a les 2:30 AM
"""

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pathlib import Path
import threading
import sys
import os
import time

# Afegir src/ al path per poder importar
sys.path.insert(0, str(Path(__file__).parent))

from src.recommendation_system import RecommendationSystem

# APScheduler per tasques automàtiques
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


# Configuració Flask
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
CORS(app)
app.config["DEBUG"] = False  # Canviat a False per producció
app.config["PORT"] = 5000

# Configuració de rutes
DATA_DIR = Path(__file__).resolve().parent / 'data'
ANIME_CSV = DATA_DIR / 'anime.csv'
RATING_CSV = DATA_DIR / 'cleaned_data.csv'

print("="*70)
print("🚀 INICIALITZANT SISTEMA DE RECOMANACIONS")
print("="*70)
print(f"\n📂 Cercant fitxers:")
print(f"  - {ANIME_CSV}")
print(f"  - {RATING_CSV}")

# Variable global pel sistema de recomanacions
rec_system = None
training_in_progress = False  # Flag per saber si s'està entrenant
last_model_check = None  # Per al model watcher


def initialize_system():
    """
    Inicialitza el sistema de recomanacions
    """
    global rec_system
    try:
        rec_system = RecommendationSystem(
            anime_csv_path=ANIME_CSV,
            rating_csv_path=RATING_CSV
        )
        print("\n✅ Sistema carregat correctament!")
        return True
    except FileNotFoundError as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("\n" + "="*70)
        return False
    except Exception as e:
        print(f"\n❌ ERROR INESPERAT: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\n" + "="*70)
        return False


def check_for_new_models():
    """
    Comprova si hi ha models nous disponibles i els carrega automàticament
    S'executa cada 30 segons per detectar models entrenats manualment
    """
    global rec_system, last_model_check
    
    if rec_system is None or training_in_progress:
        return
    
    try:
        latest_version = rec_system._get_latest_version()
        
        if latest_version > rec_system.current_model_version:
            print(f"\n🔔 NOU MODEL DETECTAT: v{latest_version}")
            print(f"   Model actual: v{rec_system.current_model_version}")
            print(f"   Recarregant automàticament...")
            
            if rec_system.reload_model():
                print(f"✅ Model v{latest_version} carregat amb èxit!")
                last_model_check = time.time()
            else:
                print(f"⚠️  No s'ha pogut carregar el model v{latest_version}")
    except Exception as e:
        pass  # Silenciosament ignorar errors en el watcher


def check_and_retrain():
    """
    Comprova si les dades han canviat i reentrena el model si cal
    Aquesta funció s'executa cada dia a les 2:30 AM
    """
    global rec_system, training_in_progress
    
    print("\n" + "="*70)
    print("🕐 COMPROVACIÓ AUTOMÀTICA DIÀRIA - 2:30 AM")
    print("="*70)
    
    if rec_system is None:
        print("⚠️  Sistema no inicialitzat. Saltant comprovació.")
        return
    
    if training_in_progress:
        print("⚠️  Ja hi ha un entrenament en curs. Saltant comprovació.")
        return
    
    # Comprovar si les dades han canviat
    if not rec_system.has_data_changed():
        print("✅ Les dades no han canviat. No cal reentrenar.")
        print("="*70)
        return
    
    print("🔔 DADES NOVES DETECTADES!")
    print("🚀 Iniciant entrenament del model en background...")
    print("="*70)
    
    # Entrenar en un thread separat per no bloquejar l'app
    training_thread = threading.Thread(target=train_model_background)
    training_thread.daemon = True
    training_thread.start()


def train_model_background():
    """
    Entrena el model en background sense bloquejar l'aplicació
    Un cop acabat, recarrega el model nou automàticament
    """
    global rec_system, training_in_progress
    
    training_in_progress = True
    
    try:
        print("\n🎓 ENTRENAMENT EN BACKGROUND INICIAT")
        print("⏱️  Això pot trigar uns minuts...")
        
        # Entrenar el model (això triga)
        rec_system.train_model(save=True)
        
        print("\n🔄 Model entrenat! Recarregant...")
        
        # Recarregar el model nou
        if rec_system.reload_model():
            print("✅ Model nou carregat correctament!")
            print(f"📦 Ara s'està usant la versió v{rec_system.current_model_version}")
        else:
            print("⚠️  No s'ha pogut recarregar el model nou")
        
    except Exception as e:
        print(f"❌ Error durant l'entrenament: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        training_in_progress = False
        print("="*70)


def setup_scheduler():
    """
    Configura el scheduler per:
    1. Executar check_and_retrain cada dia a les 2:30 AM
    2. Comprovar nous models cada 30 segons
    """
    scheduler = BackgroundScheduler()
    
    # Trigger 1: Comprovació diària a les 2:30 AM
    trigger_daily = CronTrigger(hour=2, minute=30)
    
    scheduler.add_job(
        func=check_and_retrain,
        trigger=trigger_daily,
        id='daily_model_check',
        name='Comprovació diària del model',
        replace_existing=True
    )
    
    # Trigger 2: Comprovar nous models cada 30 segons (per detectar entrenaments manuals)
    scheduler.add_job(
        func=check_for_new_models,
        trigger='interval',
        seconds=30,
        id='model_watcher',
        name='Vigilant de models nous',
        replace_existing=True
    )
    
    scheduler.start()
    
    print("\n⏰ SCHEDULER CONFIGURAT")
    print(f"   📅 Comprovació automàtica: cada dia a les 2:30 AM")
    print(f"   🔍 Vigilant de models: cada 30 segons")
    print(f"   🤖 Recarregarà automàticament models nous")
    
    return scheduler


# ============================================================================
# ENDPOINTS DE L'API
# ============================================================================

@app.route('/', methods=['GET'])
def home():
    """Pàgina principal"""
    return render_template('index.html')


@app.route('/api/model-info', methods=['GET'])
def get_model_info():
    """
    Endpoint per obtenir informació sobre el model actual
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
            "error": "Sistema no inicialitzat"
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
    Endpoint per obtenir recomanacions basades en un anime
    POST: { "anime": "Death Note", "rating": 4.5 }
    """
    if rec_system is None:
        return jsonify({
            "error": "El sistema no està inicialitzat. "
                     "Executa 'python scripts/train_model.py' primer."
        }), 503
    
    try:
        data = request.get_json()
        anime_name = data.get('anime')
        rating = data.get('rating', 5)  # Default 5 si no s'especifica
        
        if not anime_name:
            return jsonify({
                "error": "El paràmetre 'anime' és obligatori"
            }), 400
        
        # Cercar animes coincidents
        matching_animes = rec_system.search_anime_exact(anime_name)
        
        # Si hi ha múltiples coincidències, retornar-les per escollir
        if len(matching_animes) > 1:
            return jsonify({
                "status": "multiple_matches",
                "message": f"S'han trobat {len(matching_animes)} animes amb aquest nom",
                "matches": matching_animes[:10],  # Màxim 10 resultats
                "query": anime_name
            }), 300  # HTTP 300 Multiple Choices
        
        # Si només hi ha una coincidència o cap
        if len(matching_animes) == 1:
            anime_name = matching_animes[0]['name']
        
        # Obtenir recomanacions ajustades segons la valoració
        recommendations = rec_system.get_recommendations_adjusted(
            anime_name=anime_name,
            user_rating=rating,
            num_recommendations=6
        )
        
        if recommendations is None:
            return jsonify({
                "error": f"No s'ha trobat l'anime '{anime_name}'. "
                         "Prova amb una cerca més específica."
            }), 404
        
        return jsonify({
            "anime": anime_name,
            "user_rating": rating,
            "recommendations": recommendations
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": f"Error intern del servidor: {str(e)}"
        }), 500


@app.route('/api/recommendations-multiple', methods=['POST'])
def get_recommendations_multiple():
    """
    Endpoint per obtenir recomanacions basades en múltiples animes
    POST: { "ratings": { "Death Note": 5, "Code Geass": 4.5 } }
    """
    if rec_system is None:
        return jsonify({
            "error": "Sistema no inicialitzat"
        }), 503
    
    try:
        data = request.get_json()
        ratings = data.get('ratings')
        
        if not ratings or not isinstance(ratings, dict):
            return jsonify({
                "error": "El paràmetre 'ratings' és obligatori i ha de ser un diccionari"
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
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": f"Error intern: {str(e)}"
        }), 500


@app.route('/api/animes', methods=['GET'])
def get_animes():
    """Retorna la llista de tots els animes disponibles"""
    if rec_system is None:
        return jsonify({"error": "Sistema no inicialitzat"}), 503
    
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
    """Cerca animes pel nom"""
    if rec_system is None:
        return jsonify({"error": "Sistema no inicialitzat"}), 503
    
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify({
                "error": "El paràmetre 'q' és obligatori"
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
    """Llista tots els models disponibles"""
    if rec_system is None:
        return jsonify({"error": "Sistema no inicialitzat"}), 503
    
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
    Endpoint per forçar un entrenament manual del model
    POST /api/train
    """
    global training_in_progress
    
    if rec_system is None:
        return jsonify({"error": "Sistema no inicialitzat"}), 503
    
    if training_in_progress:
        return jsonify({
            "error": "Ja hi ha un entrenament en curs. Espera que acabi."
        }), 409
    
    # Iniciar entrenament en background
    training_thread = threading.Thread(target=train_model_background)
    training_thread.daemon = True
    training_thread.start()
    
    return jsonify({
        "message": "Entrenament iniciat en background",
        "training_in_progress": True
    })


# ============================================================================
# INICIALITZACIÓ I EXECUCIÓ
# ============================================================================

if __name__ == '__main__':
    # Inicialitzar el sistema
    if initialize_system():
        print("\n" + "="*70)
        print("✅ SERVIDOR FLASK INICIAT CORRECTAMENT")
        print("="*70)
        print(f"📊 Sistema carregat amb:")
        print(f"  - {len(rec_system.animes_dict)} animes")
        print(f"  - {len(rec_system.users_dict)} usuaris")
        print(f"  - Model v{rec_system.current_model_version}")
        
        # Configurar scheduler automàtic
        scheduler = setup_scheduler()
        
        try:
            # El host ha de ser '0.0.0.0' per acceptar connexions externes
            # NO pot ser una URL com 'https://recomanador.hermes.cat'
            host = '0.0.0.0'  # Això permet accés des de qualsevol IP
            port = int(os.environ.get('PORT', 5000))
            
            print(f"\n🌐 Servidor iniciat!")
            print(f"  - Local: http://localhost:{port}")
            print(f"  - Xarxa: http://0.0.0.0:{port}")
            print(f"  - Producció: https://recomanador.hermes.cat")
            print("="*70 + "\n")
            
            app.run(debug=True, host=host, port=port, use_reloader=False)
            
        except (KeyboardInterrupt, SystemExit):
            # Aturar el scheduler quan es tanca l'app
            scheduler.shutdown()
            print("\n👋 Scheduler aturat. Adéu!")
    else:
        print("\n" + "="*70)
        print("❌ NO ES POT INICIAR EL SERVIDOR")
        print("="*70)
        print("\n🔧 Per solucionar:")
        print("  1. Executa: python scripts/train_model.py")
        print("  2. O executa: ./scripts/train_auto.sh")
        print("  3. Torna a executar: python app.py")
        print("="*70 + "\n")
