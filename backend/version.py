"""Application version loaded from the active runtime configuration."""

from backend.runtime_config import load_config

_FALLBACK_VERSION = "0.0.0-dev"


def _load_version() -> str:
    try:
        version = load_config().get("version")
        if isinstance(version, str) and version.strip():
            return version.strip()
    except AttributeError:
        pass
    return _FALLBACK_VERSION


APP_VERSION = _load_version()
