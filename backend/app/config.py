from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://appuser:apppassword@localhost:5432/creative_opt"
    ollama_base_url: str = "http://localhost:11434"
    storage_path: str = "/tmp/uploads"
    max_image_size_bytes: int = 20 * 1024 * 1024
    max_video_size_bytes: int = 500 * 1024 * 1024
    phash_duplicate_threshold: int = 10
    benchmark_corpus_path: str = "data/benchmark/corpus.json"
    anthropic_api_key: str = ""
    analysis_provider: Literal["claude", "ollama"] = "claude"

    class Config:
        env_file = ".env"


settings = Settings()
