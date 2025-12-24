from typing import List, Optional, Tuple, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        num_recommendations: int = None,
        offset: int = 0
    ) -> Tuple[Optional[List[Dict]], Optional[Media], int]:
        """
        Get recommendations based on a title or media_id.

        Args:
            title: Media title to base recommendations on
            media_id: Optional specific media ID (if known)
            num_recommendations: Number of results (default from config)
            offset: Starting position for pagination

        Returns:
            Tuple of (recommendations list, source media object, total available)
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
            return None, None, 0

        # Step 2: Gather candidates from multiple sources
        candidates = self._gather_candidates(source_media)

        # Step 3: Calculate similarity and rank
        ranked = self.similarity.rank_candidates(source_media, candidates)
        total_available = len(ranked)

        # Step 4: Format results with pagination
        recommendations = []
        for media, similarity in ranked[offset:offset + num_recs]:
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

        return recommendations, source_media, total_available

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
        Optimized with parallel API calls.
        """
        # Check cache first
        cached_similar = self.cache.get_similar(source.id)
        if cached_similar:
            return cached_similar

        candidates = []
        tasks = []

        # Prepare all API tasks to run in parallel
        with ThreadPoolExecutor(max_workers=6) as executor:
            # Strategy 1: Get API's own recommendations
            if source.source in [MediaSource.TMDB_MOVIE, MediaSource.TMDB_TV]:
                tasks.append(executor.submit(self.tmdb.get_similar, source, 20))
            elif source.source == MediaSource.ANILIST:
                tasks.append(executor.submit(self.anilist.get_similar, source, 20))

            # Strategy 2 & 3: Genre-based searches (parallel)
            if source.genres:
                genres_list = list(source.genres)[:2]

                for genre in genres_list:
                    # Cross-source searches
                    if source.source == MediaSource.ANILIST:
                        tasks.append(executor.submit(self.tmdb.search, genre, 'multi', 8))
                    else:
                        tasks.append(executor.submit(self.anilist.search, genre, 8))

                # Same-source genre search for primary genre
                if genres_list:
                    primary = genres_list[0]
                    if source.source != MediaSource.ANILIST:
                        tasks.append(executor.submit(self.tmdb.search, primary, 'multi', 10))
                    tasks.append(executor.submit(self.anilist.search, primary, 10))

            # Collect results as they complete
            for future in as_completed(tasks):
                try:
                    result = future.result()
                    if result:
                        candidates.extend(result)
                except Exception as e:
                    print(f"Task error: {e}")

        # Deduplicate and filter
        seen_ids = {source.id}
        unique_candidates = []
        needs_details = []

        for c in candidates:
            if c.id in seen_ids:
                continue
            seen_ids.add(c.id)

            if not c.genres:
                needs_details.append(c)
            else:
                unique_candidates.append(c)

        # Fetch missing details in parallel (limit to avoid too many requests)
        if needs_details:
            with ThreadPoolExecutor(max_workers=4) as executor:
                detail_futures = {
                    executor.submit(self._get_media_details, c.id): c
                    for c in needs_details[:15]  # Limit to prevent too many API calls
                }

                for future in as_completed(detail_futures):
                    try:
                        detailed = future.result()
                        if detailed:
                            unique_candidates.append(detailed)
                    except Exception:
                        pass

        # Cache the candidates
        self.cache.set_similar(source.id, unique_candidates)

        return unique_candidates

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
