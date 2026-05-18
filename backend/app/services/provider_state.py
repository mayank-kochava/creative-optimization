from app.config import settings
from app.services.analysis_provider import OllamaProvider
from app.services.claude_provider import ClaudeProvider

# Valid provider names
PROVIDERS = ("claude", "ollama")

# Active provider name — reads default from config on startup
_active: str = settings.analysis_provider if settings.analysis_provider in PROVIDERS else "claude"


def get_active_name() -> str:
    return _active


def set_active(name: str) -> None:
    global _active
    if name not in PROVIDERS:
        raise ValueError(f"Unknown provider: {name}. Valid: {PROVIDERS}")
    _active = name


def get_active_provider() -> OllamaProvider | ClaudeProvider:
    if _active == "claude":
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set in .env")
        return ClaudeProvider(api_key=settings.anthropic_api_key)
    return OllamaProvider(base_url=settings.ollama_base_url)
