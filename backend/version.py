"""Application version loaded from the repository's configuration source."""

import json
from pathlib import Path


_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "app_config.json"
_FALLBACK_VERSION = "0.0.0-dev"


def _load_version() -> str:
    try:
        with _CONFIG_PATH.open(encoding="utf-8") as config_file:
            version = json.load(config_file).get("version")
        if isinstance(version, str) and version.strip():
            return version.strip()
    except (OSError, json.JSONDecodeError, AttributeError):
        pass
    return _FALLBACK_VERSION


APP_VERSION = _load_version()
