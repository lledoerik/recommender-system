from typing import List, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import Config
from src.models.media import Media, MediaSource
from src.api_clients.base_client import BaseAPIClient, RateLimiter


class TMDBClient(BaseAPIClient):
    """TMDB API client for movies and TV series"""

    def __init__(self):
        super().__init__(RateLimiter(Config.TMDB_RATE_LIMIT, 10))
        self.api_key = Config.TMDB_API_KEY
        self.base_url = Config.TMDB_BASE_URL

    def _make_request(self, endpoint: str, params: dict = None) -> dict:
        """Make a rate-limited request to TMDB API"""
        self.rate_limiter.wait_if_needed()
        params = params or {}
        params['api_key'] = self.api_key

        response = self.session.get(f"{self.base_url}{endpoint}", params=params)
        response.raise_for_status()
        return response.json()

    def search(self, query: str, media_type: str = 'multi', limit: int = 10) -> List[Media]:
        """
        Search TMDB for movies/TV shows
        media_type: 'movie', 'tv', or 'multi' (both)
        """
        results = []

        try:
            if media_type == 'multi':
                data = self._make_request('/search/multi', {'query': query})
            elif media_type == 'movie':
                data = self._make_request('/search/movie', {'query': query})
            else:
                data = self._make_request('/search/tv', {'query': query})

            for item in data.get('results', [])[:limit]:
                item_type = item.get('media_type', media_type)
                if item_type in ['movie', 'tv']:
                    results.append(self._parse_search_result(item, item_type))
        except Exception as e:
            print(f"TMDB search error: {e}")

        return results

    def _parse_search_result(self, item: dict, media_type: str) -> Media:
        """Parse TMDB search result into Media object"""
        source = MediaSource.TMDB_MOVIE if media_type == 'movie' else MediaSource.TMDB_TV

        title_key = 'title' if media_type == 'movie' else 'name'
        date_key = 'release_date' if media_type == 'movie' else 'first_air_date'

        poster_path = item.get('poster_path')
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None

        return Media(
            id=f"tmdb_{media_type}_{item['id']}",
            source=source,
            title=item.get(title_key, 'Unknown'),
            original_title=item.get(f'original_{title_key}'),
            overview=item.get('overview'),
            genres=set(),
            release_year=self._extract_year(item.get(date_key)),
            poster_url=poster_url,
            rating=item.get('vote_average'),
            popularity=item.get('popularity')
        )

    def get_details(self, media_id: str) -> Optional[Media]:
        """Get full details including genres, keywords, cast - optimized with append_to_response"""
        parts = media_id.split('_')
        if len(parts) != 3:
            return None

        _, media_type, tmdb_id = parts

        try:
            # Single API call with append_to_response (3 calls -> 1 call)
            details = self._make_request(
                f'/{media_type}/{tmdb_id}',
                {'append_to_response': 'credits,keywords'}
            )

            media = self._parse_search_result(details, media_type)

            # Add genres
            media.genres = {g['name'] for g in details.get('genres', [])}

            # Add keywords (from appended response)
            keywords_data = details.get('keywords', {})
            keywords_list = keywords_data.get('keywords', keywords_data.get('results', []))
            media.keywords = {k['name'] for k in keywords_list}

            # Add cast (top 5) from appended credits
            credits = details.get('credits', {})
            cast = credits.get('cast', [])[:5]
            media.cast = [c['name'] for c in cast]

            # Add director (for movies)
            if media_type == 'movie':
                directors = [c for c in credits.get('crew', []) if c.get('job') == 'Director']
                if directors:
                    media.director = directors[0]['name']

            return media

        except Exception as e:
            print(f"TMDB get_details error: {e}")
            return None

    def get_similar(self, media: Media, limit: int = 20) -> List[Media]:
        """Get similar movies/TV shows from TMDB's recommendations"""
        parts = media.id.split('_')
        if len(parts) != 3:
            return []

        media_type, tmdb_id = parts[1], parts[2]

        try:
            data = self._make_request(f'/{media_type}/{tmdb_id}/recommendations')

            results = []
            for item in data.get('results', [])[:limit]:
                results.append(self._parse_search_result(item, media_type))

            return results

        except Exception as e:
            print(f"TMDB get_similar error: {e}")
            return []

    def _extract_year(self, date_str: str) -> Optional[int]:
        """Extract year from date string"""
        if date_str and len(date_str) >= 4:
            try:
                return int(date_str[:4])
            except ValueError:
                return None
        return None
