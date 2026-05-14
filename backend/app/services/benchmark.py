import json
from pathlib import Path

from app.config import settings


class BenchmarkService:
    def __init__(self):
        self._corpus: list[int] | None = None

    def _load_corpus(self) -> list[int]:
        if self._corpus is not None:
            return self._corpus
        corpus_path = Path(settings.benchmark_corpus_path)
        if not corpus_path.exists():
            self._corpus = []
            return self._corpus
        self._corpus = json.loads(corpus_path.read_text())
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
        percentile = max(1, 100 - round(min_dist / 64 * 99))
        return percentile
