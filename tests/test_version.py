"""Regression tests for the single application-version source of truth."""

import json
from pathlib import Path


def test_app_version_matches_config():
    from backend.version import APP_VERSION

    config_path = Path(__file__).resolve().parents[1] / "config" / "app_config.json"
    configured_version = json.loads(config_path.read_text(encoding="utf-8"))["version"]
    assert APP_VERSION == configured_version


def test_health_routes_use_app_version():
    from backend.routes.health import health_check
    from backend.version import APP_VERSION

    assert health_check()["version"] == APP_VERSION
