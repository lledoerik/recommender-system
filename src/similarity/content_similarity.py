from typing import List, Set, Tuple
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.models.media import Media


class ContentSimilarity:
    """Content-based similarity calculator using weighted Jaccard similarity"""

    # Feature weights for different attributes
    WEIGHTS = {
        'genre': 0.35,
        'keyword': 0.25,
        'cast': 0.15,
        'director': 0.10,
        'studio': 0.10,
        'year': 0.05
    }

    @staticmethod
    def jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
        """Calculate Jaccard similarity between two sets"""
        if not set1 or not set2:
            return 0.0

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        return intersection / union if union > 0 else 0.0

    @staticmethod
    def weighted_similarity(source: Media, candidate: Media) -> float:
        """
        Calculate weighted content similarity between two media items.
        Returns a score between 0.0 and 1.0
        """
        score = 0.0
        weights = ContentSimilarity.WEIGHTS

        # Genre similarity (most important)
        if source.genres and candidate.genres:
            genre_sim = ContentSimilarity.jaccard_similarity(
                source.genres, candidate.genres
            )
            score += genre_sim * weights['genre']

        # Keyword similarity
        if source.keywords and candidate.keywords:
            keyword_sim = ContentSimilarity.jaccard_similarity(
                source.keywords, candidate.keywords
            )
            score += keyword_sim * weights['keyword']

        # Cast similarity (top 5 actors)
        if source.cast and candidate.cast:
            cast_set1 = {c.lower() for c in source.cast}
            cast_set2 = {c.lower() for c in candidate.cast}
            cast_sim = ContentSimilarity.jaccard_similarity(cast_set1, cast_set2)
            score += cast_sim * weights['cast']

        # Director match (binary)
        if source.director and candidate.director:
            if source.director.lower() == candidate.director.lower():
                score += weights['director']

        # Studio similarity (for anime)
        if source.studios and candidate.studios:
            studio_set1 = {s.lower() for s in source.studios}
            studio_set2 = {s.lower() for s in candidate.studios}
            studio_sim = ContentSimilarity.jaccard_similarity(studio_set1, studio_set2)
            score += studio_sim * weights['studio']

        # Year proximity bonus (within 5 years = bonus)
        if source.release_year and candidate.release_year:
            year_diff = abs(source.release_year - candidate.release_year)
            if year_diff <= 5:
                year_bonus = (5 - year_diff) / 5
                score += year_bonus * weights['year']

        return min(score, 1.0)

    @staticmethod
    def rank_candidates(
        source: Media,
        candidates: List[Media],
        min_similarity: float = 0.1
    ) -> List[Tuple[Media, float]]:
        """
        Rank candidates by similarity to source.
        Returns list of (media, similarity_score) tuples, sorted descending.
        """
        scored = []
        seen_ids = set()

        for candidate in candidates:
            # Skip duplicates and same item
            if candidate.id == source.id or candidate.id in seen_ids:
                continue
            seen_ids.add(candidate.id)

            similarity = ContentSimilarity.weighted_similarity(source, candidate)

            if similarity >= min_similarity:
                scored.append((candidate, similarity))

        # Sort by similarity (descending), then by rating (descending)
        scored.sort(
            key=lambda x: (x[1], x[0].rating or 0),
            reverse=True
        )

        return scored
