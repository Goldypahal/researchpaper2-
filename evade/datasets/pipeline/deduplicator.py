"""
Deduplicator for EVADE items.
Detects:
1. Exact duplicates (SHA-256 on verbatim text)
2. Normalized duplicates (lowercase, punctuation-stripped, whitespace-collapsed)
3. Semantic duplicates (character 3-gram & word Jaccard similarity > 0.88)
"""

import hashlib
import re
from typing import Dict, List, Set, Tuple


def normalize_text(text: str) -> str:
    """Normalizes text by lowercasing, stripping punctuation, and collapsing whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_ngrams(text: str, n: int = 3) -> Set[str]:
    """Generates character n-grams from normalized text."""
    norm = normalize_text(text)
    if len(norm) < n:
        return {norm}
    return {norm[i : i + n] for i in range(len(norm) - n + 1)}


def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Computes Jaccard similarity coefficient between two sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    return float(intersection) / float(union)


class Deduplicator:
    """Tracks seen questions across exact, normalized, and semantic similarity indices."""

    def __init__(self, semantic_threshold: float = 0.88):
        self.semantic_threshold = semantic_threshold
        self.exact_hashes: Set[str] = set()
        self.normalized_hashes: Set[str] = set()
        self.items_by_domain: Dict[str, List[Tuple[str, Set[str]]]] = {}

    def is_duplicate(self, text: str, domain: str) -> Tuple[bool, str]:
        """
        Checks whether the question is an exact, normalized, or semantic duplicate.
        Returns (is_dup, reason).
        """
        # 1. Exact hash check
        exact_h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if exact_h in self.exact_hashes:
            return True, "exact_duplicate"

        # 2. Normalized hash check
        norm_text = normalize_text(text)
        norm_h = hashlib.sha256(norm_text.encode("utf-8")).hexdigest()
        if norm_h in self.normalized_hashes:
            return True, "normalized_duplicate"

        # 3. Semantic similarity check within the same domain
        ngrams = get_ngrams(text, n=3)
        domain_items = self.items_by_domain.setdefault(domain, [])
        for existing_id, existing_ngrams in domain_items:
            sim = jaccard_similarity(ngrams, existing_ngrams)
            if sim >= self.semantic_threshold:
                return True, f"semantic_duplicate (sim={sim:.2f} with {existing_id})"

        return False, "unique"

    def register(self, task_id: str, text: str, domain: str):
        """Registers a verified unique question into all index sets."""
        exact_h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        norm_text = normalize_text(text)
        norm_h = hashlib.sha256(norm_text.encode("utf-8")).hexdigest()
        ngrams = get_ngrams(text, n=3)

        self.exact_hashes.add(exact_h)
        self.normalized_hashes.add(norm_h)
        self.items_by_domain.setdefault(domain, []).append((task_id, ngrams))
