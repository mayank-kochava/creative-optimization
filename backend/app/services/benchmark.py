import json
from pathlib import Path

from app.config import settings


class BenchmarkService:
    _HASH_BITS = 64  # phash with hash_size=8 produces 8×8=64 bit hash

    def __init__(self):
        self._corpus: list[int] | None = None

    def _load_corpus(self) -> list[int]:
        if self._corpus is not None:
            return self._corpus
        corpus_path = Path(settings.benchmark_corpus_path)
        if not corpus_path.exists():
            self._corpus = []
            return self._corpus
        try:
            data = json.loads(corpus_path.read_text())
            if not isinstance(data, list):
                self._corpus = []
                return self._corpus
            self._corpus = [int(h) for h in data if isinstance(h, (int, str))]
        except (json.JSONDecodeError, ValueError):
            self._corpus = []
        return self._corpus

    def compute_percentile(self, phash: int) -> int | None:
        """
        Return the percentile rank of phash against benchmark corpus.
        Lower minimum Hamming distance → more similar to known ads → higher percentile.
        Returns None if corpus is empty.
        Returns int in [1, 100].
        """
        corpus = self._load_corpus()
        if not corpus:
            return None
        min_dist = min(bin(phash ^ h).count("1") for h in corpus)
        # Distance 0 = identical = top percentile, distance 64 (max) = bottom
        percentile = max(1, 100 - round(min_dist / self._HASH_BITS * 99))
        return percentile
