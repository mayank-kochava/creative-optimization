import json
import pytest
from pathlib import Path


def test_corpus_file_exists_after_setup():
    """Run setup and verify corpus.json is created with expected hashes."""
    import subprocess
    import sys
    backend_dir = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, "scripts/setup_benchmark.py", "--max-images", "50"],
        cwd=str(backend_dir),
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    corpus_path = backend_dir / "data" / "benchmark" / "corpus.json"
    assert corpus_path.exists()
    hashes = json.loads(corpus_path.read_text())
    assert len(hashes) >= 50
    assert all(isinstance(h, int) for h in hashes)


def test_benchmark_service_returns_percentile():
    from app.services.benchmark import BenchmarkService
    corpus = [0xABCDEF1234567890, 0x1111111111111111, 0x0000000000000000]
    svc = BenchmarkService()
    svc._corpus = corpus
    p = svc.compute_percentile(0xABCDEF1234567890)
    assert p == 100

    p2 = svc.compute_percentile(0x5432101234567890)
    assert p2 is not None
    assert 1 <= p2 <= 100


def test_benchmark_service_returns_none_for_empty_corpus():
    from app.services.benchmark import BenchmarkService
    svc = BenchmarkService()
    svc._corpus = []
    assert svc.compute_percentile(12345) is None
