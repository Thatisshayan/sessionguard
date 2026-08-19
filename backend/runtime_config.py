"""
backend/runtime_config.py
-------------------------
Resolve the writable runtime config location.

In development this remains repo-root ``config/app_config.json``.
In packaged desktop runs, ``SG_DATA_DIR`` points at the writable app-data
directory, so the config is copied there on first access and all subsequent
reads/writes stay out of the installed bundle.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from database.db import BASE_DIR


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "app_config.json"
RUNTIME_CONFIG_PATH = BASE_DIR / "config" / "app_config.json"


def get_config_path() -> Path:
    """Return the active config path, seeding a writable copy when needed."""
    if RUNTIME_CONFIG_PATH.exists():
        return RUNTIME_CONFIG_PATH

    RUNTIME_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    if DEFAULT_CONFIG_PATH.exists() and DEFAULT_CONFIG_PATH.resolve() != RUNTIME_CONFIG_PATH.resolve():
        shutil.copy2(DEFAULT_CONFIG_PATH, RUNTIME_CONFIG_PATH)
    elif not RUNTIME_CONFIG_PATH.exists():
        RUNTIME_CONFIG_PATH.write_text("{}", encoding="utf-8")

    return RUNTIME_CONFIG_PATH


def load_config() -> dict[str, Any]:
    """Read the active runtime config file."""
    try:
        return json.loads(get_config_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return {}


def save_config(cfg: dict[str, Any]) -> Path:
    """Persist config to the writable runtime config file."""
    config_path = get_config_path()
    config_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return config_path
