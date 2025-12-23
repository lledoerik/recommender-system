from abc import ABC, abstractmethod
from typing import List, Optional
import time
import requests


class RateLimiter:
    """Simple rate limiter to prevent API throttling"""

    def __init__(self, max_requests: int, period_seconds: int):
        self.max_requests = max_requests
        self.period = period_seconds
        self.requests: List[float] = []

    def wait_if_needed(self):
        now = time.time()
        # Remove old requests outside the time window
        self.requests = [t for t in self.requests if now - t < self.period]

        if len(self.requests) >= self.max_requests:
            sleep_time = self.period - (now - self.requests[0])
            if sleep_time > 0:
                time.sleep(sleep_time)

        self.requests.append(time.time())


class BaseAPIClient(ABC):
    """Abstract base class for API clients"""

    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
        self.session = requests.Session()

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> List:
        """Search for media by title"""
        pass

    @abstractmethod
    def get_details(self, media_id: str) -> Optional[object]:
        """Get full details for a media item"""
        pass

    @abstractmethod
    def get_similar(self, media, limit: int = 20) -> List:
        """Get similar items from this source's API"""
        pass
