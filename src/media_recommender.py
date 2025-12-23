from typing import List, Optional, Tuple, Dict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from src.models.media import Media, MediaSource
from src.api_clients.tmdb_client import TMDBClient
from src.api_clients.anilist_client import AniListClient
from src.similarity.content_similarity import ContentSimilarity
from src.cache.media_cache import MediaCache


class MediaRecommendationSystem:
    """
    Multi-source media recommendation system.
    Supports TMDB (movies/TV) and AniList (anime).
    Uses content-based similarity for recommendations.
    """

    def __init__(self):
        self.tmdb = TMDBClient()
        self.anilist = AniListClient()
        self.cache = MediaCache()
        self.similarity = ContentSimilarity()

    def search(self, query: str, source: str = 'all') -> List[Media]:
        """
        Search for media across sources.

        Args:
            query: Search term
            source: 'tmdb', 'anilist', or 'all' (default)

        Returns:
            List of Media objects
        """
        results = []

        if source in ['all', 'tmdb']:
            cached = self.cache.get_search(query, 'tmdb')
            if cached:
                results.extend(cached)
            else:
                tmdb_results = self.tmdb.search(query, 'multi')
                self.cache.set_search(query, 'tmdb', tmdb_results)
                results.extend(tmdb_results)

        if source in ['all', 'anilist']:
            cached = self.cache.get_search(query, 'anilist')
            if cached:
                results.extend(cached)
            else:
                anilist_results = self.anilist.search(query)
                self.cache.set_search(query, 'anilist', anilist_results)
                results.extend(anilist_results)

        # Sort by popularity
        results.sort(key=lambda x: x.popularity or 0, reverse=True)

        return results[:20]

    def get_recommendations(
        self,
        title: str = None,
        media_id: str = None,
        num_recommendations: int = None
    ) -> Tuple[Optional[List[Dict]], Optional[Media]]:
        """
        Get recommendations based on a title or media_id.

        Args:
            title: Media title to base recommendations on
            media_id: Optional specific media ID (if known)
            num_recommendations: Number of results (default from config)

        Returns:
            Tuple of (recommendations list, source media object)
        """
        num_recs = num_recommendations or Config.NUM_RECOMMENDATIONS

        # Step 1: Find the source media
        source_media = None

        if media_id:
            source_media = self._get_media_details(media_id)
        elif title:
            search_results = self.search(title)
            if search_results:
                source_media = self._get_media_details(search_results[0].id)

        if not source_media:
            return None, None

        # Step 2: Gather candidates from multiple sources
        candidates = self._gather_candidates(source_media)

        # Step 3: Calculate similarity and rank
        ranked = self.similarity.rank_candidates(source_media, candidates)

        # Step 4: Format results
        recommendations = []
        for media, similarity in ranked[:num_recs]:
            recommendations.append({
                "id": media.id,
                "title": media.title,
                "original_title": media.original_title,
                "source": media.source.value,
                "score": round(media.rating, 1) if media.rating else None,
                "genre": ", ".join(sorted(media.genres)[:3]) if media.genres else None,
                "year": media.release_year,
                "poster_url": media.poster_url,
                "similarity": round(similarity, 2),
                "overview": (
                    media.overview[:200] + "..."
                    if media.overview and len(media.overview) > 200
                    else media.overview
                )
            })

        return recommendations, source_media

    def _get_media_details(self, media_id: str) -> Optional[Media]:
        """Get full details for a media item, with caching"""
        cached = self.cache.get_media(media_id)
        if cached:
            return cached

        media = None
        if media_id.startswith('tmdb_'):
            media = self.tmdb.get_details(media_id)
        elif media_id.startswith('anilist_'):
            media = self.anilist.get_details(media_id)

        if media:
            self.cache.set_media(media)

        return media

    def _gather_candidates(self, source: Media) -> List[Media]:
        """
        Gather candidate recommendations from all relevant sources.
        Uses API's own recommendations + genre-based search.
        """
        candidates = []

        # Check cache first
        cached_similar = self.cache.get_similar(source.id)
        if cached_similar:
            return cached_similar

        # Strategy 1: Get API's own recommendations
        if source.source in [MediaSource.TMDB_MOVIE, MediaSource.TMDB_TV]:
            api_recs = self.tmdb.get_similar(source, limit=20)
            candidates.extend(api_recs)
        elif source.source == MediaSource.ANILIST:
            api_recs = self.anilist.get_similar(source, limit=20)
            candidates.extend(api_recs)

        # Strategy 2: Search by primary genre across sources
        if source.genres:
            genres_list = list(source.genres)
            primary_genre = genres_list[0] if genres_list else None

            if primary_genre:
                # Search TMDB by genre keywords
                if source.source != MediaSource.ANILIST:
                    genre_results = self.tmdb.search(primary_genre, 'multi')
                    candidates.extend(genre_results[:10])

                # Search AniList by genre
                genre_results = self.anilist.search(primary_genre)
                candidates.extend(genre_results[:10])

        # Strategy 3: Cross-source recommendations
        if source.source == MediaSource.ANILIST and source.genres:
            # If source is anime, search TMDB for similar genres
            for genre in list(source.genres)[:2]:
                tmdb_results = self.tmdb.search(genre, 'multi')
                candidates.extend(tmdb_results[:5])
        elif source.source in [MediaSource.TMDB_MOVIE, MediaSource.TMDB_TV] and source.genres:
            # If source is movie/TV, search AniList for similar genres
            for genre in list(source.genres)[:2]:
                anilist_results = self.anilist.search(genre)
                candidates.extend(anilist_results[:5])

        # Get full details for candidates that don't have genres
        detailed_candidates = []
        seen_ids = set()

        for c in candidates:
            if c.id == source.id or c.id in seen_ids:
                continue
            seen_ids.add(c.id)

            if not c.genres:
                detailed = self._get_media_details(c.id)
                if detailed:
                    detailed_candidates.append(detailed)
            else:
                detailed_candidates.append(c)

        # Cache the candidates
        self.cache.set_similar(source.id, detailed_candidates)

        return detailed_candidates

    def get_system_info(self) -> Dict:
        """Return system information"""
        cache_stats = self.cache.stats()
        return {
            'sources': ['TMDB', 'AniList'],
            'tmdb_configured': bool(Config.TMDB_API_KEY and Config.TMDB_API_KEY != 'your_tmdb_api_key_here'),
            'num_recommendations': Config.NUM_RECOMMENDATIONS,
            'cache_ttl': Config.CACHE_TTL,
            'cache_stats': cache_stats
        }
