import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    # API Keys
    TMDB_API_KEY = os.getenv('TMDB_API_KEY')
    TMDB_BASE_URL = 'https://api.themoviedb.org/3'

    # AniList uses GraphQL, no API key required
    ANILIST_API_URL = 'https://graphql.anilist.co'

    # Cache settings
    CACHE_TTL = 3600  # 1 hour

    # Recommendation settings
    NUM_RECOMMENDATIONS = 10

    # Rate limiting
    TMDB_RATE_LIMIT = 40  # requests per 10 seconds
    ANILIST_RATE_LIMIT = 90  # requests per minute
