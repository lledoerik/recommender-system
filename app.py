from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pathlib import Path
import sys
import os

# Add src/ to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.media_recommender import MediaRecommendationSystem

# Flask configuration
app = Flask(__name__,
            static_folder='static',
            template_folder='templates')
CORS(app)
app.config["DEBUG"] = False

print("=" * 70)
print("INITIALIZING MEDIA RECOMMENDATION SYSTEM")
print("=" * 70)

# Global variable for recommendation system
rec_system = None

try:
    rec_system = MediaRecommendationSystem()
    system_info = rec_system.get_system_info()
    print("\nSystem initialized successfully!")
    print(f"  - Sources: {', '.join(system_info['sources'])}")
    print(f"  - TMDB configured: {system_info['tmdb_configured']}")
    print(f"  - Recommendations per request: {system_info['num_recommendations']}")
    print("=" * 70)
except Exception as e:
    print(f"\nERROR initializing system: {e}")
    import traceback
    traceback.print_exc()
    print("=" * 70)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/', methods=['GET'])
def home():
    """Main page"""
    return render_template('index.html')


@app.route('/api/system-info', methods=['GET'])
def get_system_info():
    """
    Get system information
    GET /api/system-info

    Returns:
        {
            "sources": ["TMDB", "AniList"],
            "tmdb_configured": true,
            "num_recommendations": 10,
            "cache_ttl": 3600,
            "cache_stats": {...}
        }
    """
    if rec_system is None:
        return jsonify({"error": "System not initialized"}), 503

    return jsonify(rec_system.get_system_info())


@app.route('/api/search', methods=['GET'])
def search_media():
    """
    Search for media by title.
    GET /api/search?q=inception&source=all

    Query params:
        q: Search query (required)
        source: 'tmdb', 'anilist', or 'all' (default: 'all')
    """
    if rec_system is None:
        return jsonify({"error": "System not initialized"}), 503

    query = request.args.get('q', '')
    source = request.args.get('source', 'all')

    if not query:
        return jsonify({"error": "Parameter 'q' is required"}), 400

    try:
        results = rec_system.search(query, source)
        return jsonify({
            "results": [
                {
                    "id": m.id,
                    "title": m.title,
                    "source": m.source.value,
                    "year": m.release_year,
                    "genre": ", ".join(list(m.genres)[:3]) if m.genres else None,
                    "poster_url": m.poster_url,
                    "rating": round(m.rating, 1) if m.rating else None
                }
                for m in results
            ],
            "count": len(results)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/recommendations', methods=['POST'])
def get_recommendations():
    """
    Get recommendations based on a media title.
    POST: { "title": "Inception" } or { "media_id": "tmdb_movie_27205" }

    Returns 10 recommendations based on content similarity.
    """
    if rec_system is None:
        return jsonify({"error": "System not initialized"}), 503

    try:
        data = request.get_json()
        title = data.get('title')
        media_id = data.get('media_id')

        if not title and not media_id:
            return jsonify({
                "error": "Parameter 'title' or 'media_id' is required"
            }), 400

        # If searching by title and no media_id, first search
        if title and not media_id:
            search_results = rec_system.search(title)

            if not search_results:
                return jsonify({
                    "error": f"No results found for '{title}'"
                }), 404

            # If multiple results from different sources or with different titles, let user choose
            unique_items = set(
                (r.title.lower(), r.source.value, r.release_year)
                for r in search_results[:5]
            )
            if len(unique_items) > 1:
                return jsonify({
                    "status": "multiple_matches",
                    "message": f"Found multiple matches for '{title}'",
                    "matches": [
                        {
                            "id": r.id,
                            "title": r.title,
                            "source": r.source.value,
                            "year": r.release_year,
                            "genre": ", ".join(list(r.genres)[:3]) if r.genres else None,
                            "poster_url": r.poster_url
                        }
                        for r in search_results[:10]
                    ],
                    "query": title
                }), 300

            # Single match - use its ID
            media_id = search_results[0].id

        # Get recommendations
        recommendations, source_media = rec_system.get_recommendations(
            title=title,
            media_id=media_id
        )

        if recommendations is None or source_media is None:
            return jsonify({
                "error": f"'{title or media_id}' not found. Try a more specific search."
            }), 404

        return jsonify({
            "source": {
                "id": source_media.id,
                "title": source_media.title,
                "source_type": source_media.source.value,
                "genre": ", ".join(sorted(source_media.genres)[:3]) if source_media.genres else None,
                "year": source_media.release_year,
                "poster_url": source_media.poster_url
            },
            "recommendations": recommendations
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    if rec_system:
        host = '0.0.0.0'
        port = int(os.environ.get('PORT', 5000))

        print(f"\nServer starting!")
        print(f"  - Local: http://localhost:{port}")
        print(f"  - Network: http://0.0.0.0:{port}")
        print("=" * 70 + "\n")

        app.run(debug=False, host=host, port=port)
    else:
        print("\nCannot start server - system not initialized")
        print("Check that TMDB_API_KEY is set in .env file")
        print("Get your API key at: https://www.themoviedb.org/settings/api")
