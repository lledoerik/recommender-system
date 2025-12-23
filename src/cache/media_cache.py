from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import Config
from src.models.media import Media


class MediaCache:
    """In-memory cache for media items and search results with TTL"""

    def __init__(self, ttl_seconds: int = None):
        self.ttl = ttl_seconds or Config.CACHE_TTL
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """Check if cache entry has expired"""
        return datetime.now() > entry['expires_at']

    def get(self, key: str) -> Optional[Any]:
        """Get item from cache if exists and not expired"""
        if key in self._cache:
            entry = self._cache[key]
            if not self._is_expired(entry):
                return entry['value']
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any):
        """Set item in cache with TTL"""
        self._cache[key] = {
            'value': value,
            'expires_at': datetime.now() + timedelta(seconds=self.ttl)
        }

    def get_media(self, media_id: str) -> Optional[Media]:
        """Get cached media details"""
        return self.get(f"media:{media_id}")

    def set_media(self, media: Media):
        """Cache media details"""
        self.set(f"media:{media.id}", media)

    def get_search(self, query: str, source: str) -> Optional[List[Media]]:
        """Get cached search results"""
        return self.get(f"search:{source}:{query.lower()}")

    def set_search(self, query: str, source: str, results: List[Media]):
        """Cache search results"""
        self.set(f"search:{source}:{query.lower()}", results)

    def get_similar(self, media_id: str) -> Optional[List[Media]]:
        """Get cached similar items"""
        return self.get(f"similar:{media_id}")

    def set_similar(self, media_id: str, results: List[Media]):
        """Cache similar items"""
        self.set(f"similar:{media_id}", results)

    def clear(self):
        """Clear all cache"""
        self._cache.clear()

    def cleanup_expired(self):
        """Remove expired entries"""
        expired_keys = [
            k for k, v in self._cache.items()
            if self._is_expired(v)
        ]
        for key in expired_keys:
            del self._cache[key]

    def stats(self) -> Dict[str, int]:
        """Return cache statistics"""
        self.cleanup_expired()
        return {
            'total_entries': len(self._cache),
            'media_entries': sum(1 for k in self._cache if k.startswith('media:')),
            'search_entries': sum(1 for k in self._cache if k.startswith('search:')),
            'similar_entries': sum(1 for k in self._cache if k.startswith('similar:'))
        }
