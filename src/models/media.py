from dataclasses import dataclass, field
from typing import List, Optional, Set
from enum import Enum


class MediaSource(Enum):
    TMDB_MOVIE = "tmdb_movie"
    TMDB_TV = "tmdb_tv"
    ANILIST = "anilist"


@dataclass
class Media:
    """Generic media item (movie, TV series, or anime)"""
    id: str
    source: MediaSource
    title: str
    original_title: Optional[str] = None
    overview: Optional[str] = None
    genres: Set[str] = field(default_factory=set)
    keywords: Set[str] = field(default_factory=set)
    release_year: Optional[int] = None
    poster_url: Optional[str] = None
    rating: Optional[float] = None
    popularity: Optional[float] = None

    # TMDB-specific
    cast: List[str] = field(default_factory=list)
    director: Optional[str] = None

    # AniList-specific
    studios: List[str] = field(default_factory=list)
    season: Optional[str] = None
    episodes: Optional[int] = None

    def get_feature_vector(self) -> Set[str]:
        """Returns all features for similarity calculation"""
        features = set()
        features.update(f"genre:{g.lower()}" for g in self.genres)
        features.update(f"keyword:{k.lower()}" for k in self.keywords)
        features.update(f"cast:{c.lower()}" for c in self.cast[:5])
        if self.director:
            features.add(f"director:{self.director.lower()}")
        features.update(f"studio:{s.lower()}" for s in self.studios)
        return features
