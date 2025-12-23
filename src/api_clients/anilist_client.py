from typing import List, Optional
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import Config
from src.models.media import Media, MediaSource
from src.api_clients.base_client import BaseAPIClient, RateLimiter


class AniListClient(BaseAPIClient):
    """AniList GraphQL API client for anime"""

    SEARCH_QUERY = '''
    query ($search: String, $page: Int, $perPage: Int) {
        Page(page: $page, perPage: $perPage) {
            media(search: $search, type: ANIME, sort: POPULARITY_DESC) {
                id
                title { romaji english native }
                description
                genres
                tags { name rank }
                seasonYear
                coverImage { large }
                averageScore
                popularity
                studios { nodes { name } }
                episodes
                season
            }
        }
    }
    '''

    DETAILS_QUERY = '''
    query ($id: Int) {
        Media(id: $id, type: ANIME) {
            id
            title { romaji english native }
            description
            genres
            tags { name rank }
            seasonYear
            coverImage { large }
            averageScore
            popularity
            studios { nodes { name } }
            episodes
            season
            recommendations(sort: RATING_DESC, perPage: 20) {
                nodes {
                    mediaRecommendation {
                        id
                        title { romaji english native }
                        description
                        genres
                        tags { name rank }
                        averageScore
                        coverImage { large }
                        seasonYear
                        studios { nodes { name } }
                        episodes
                        season
                        popularity
                    }
                }
            }
        }
    }
    '''

    def __init__(self):
        super().__init__(RateLimiter(Config.ANILIST_RATE_LIMIT, 60))
        self.api_url = Config.ANILIST_API_URL

    def _make_request(self, query: str, variables: dict) -> dict:
        """Make a rate-limited GraphQL request to AniList"""
        self.rate_limiter.wait_if_needed()

        response = self.session.post(
            self.api_url,
            json={'query': query, 'variables': variables}
        )
        response.raise_for_status()
        return response.json()

    def search(self, query: str, limit: int = 10) -> List[Media]:
        """Search AniList for anime"""
        try:
            data = self._make_request(self.SEARCH_QUERY, {
                'search': query,
                'page': 1,
                'perPage': limit
            })

            results = []
            for item in data.get('data', {}).get('Page', {}).get('media', []):
                results.append(self._parse_result(item))

            return results

        except Exception as e:
            print(f"AniList search error: {e}")
            return []

    def _parse_result(self, item: dict) -> Media:
        """Parse AniList result into Media object"""
        title = item.get('title', {})

        # Get tags as keywords (filter by rank > 60 for relevance)
        tags = item.get('tags', []) or []
        keywords = {t['name'] for t in tags if t.get('rank', 0) > 60}

        # Get studios
        studios_data = item.get('studios', {}).get('nodes', []) or []
        studios = [s['name'] for s in studios_data if s.get('name')]

        return Media(
            id=f"anilist_{item['id']}",
            source=MediaSource.ANILIST,
            title=title.get('english') or title.get('romaji') or 'Unknown',
            original_title=title.get('native'),
            overview=self._clean_description(item.get('description')),
            genres=set(item.get('genres', []) or []),
            keywords=keywords,
            release_year=item.get('seasonYear'),
            poster_url=item.get('coverImage', {}).get('large') if item.get('coverImage') else None,
            rating=item.get('averageScore', 0) / 10 if item.get('averageScore') else None,
            popularity=item.get('popularity'),
            studios=studios,
            season=item.get('season'),
            episodes=item.get('episodes')
        )

    def get_details(self, media_id: str) -> Optional[Media]:
        """Get full anime details including recommendations"""
        try:
            anilist_id = int(media_id.split('_')[1])

            data = self._make_request(self.DETAILS_QUERY, {'id': anilist_id})
            media_data = data.get('data', {}).get('Media')

            if not media_data:
                return None

            return self._parse_result(media_data)

        except Exception as e:
            print(f"AniList get_details error: {e}")
            return None

    def get_similar(self, media: Media, limit: int = 20) -> List[Media]:
        """Get AniList's recommendations for an anime"""
        try:
            anilist_id = int(media.id.split('_')[1])

            data = self._make_request(self.DETAILS_QUERY, {'id': anilist_id})
            recommendations = (
                data.get('data', {})
                .get('Media', {})
                .get('recommendations', {})
                .get('nodes', [])
            )

            results = []
            for rec in recommendations[:limit]:
                rec_media = rec.get('mediaRecommendation')
                if rec_media:
                    results.append(self._parse_result(rec_media))

            return results

        except Exception as e:
            print(f"AniList get_similar error: {e}")
            return []

    def _clean_description(self, desc: str) -> str:
        """Remove HTML tags from description"""
        if not desc:
            return ''
        return re.sub(r'<[^>]+>', '', desc)
