"""Static packaging checks for every configured Tauri target."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_tauri_declares_all_supported_formats_and_backend_resource():
    config = json.loads((ROOT / "desktop_shell" / "src-tauri" / "tauri.conf.json").read_text())
    bundle = config["tauri"]["bundle"]

    assert set(bundle["targets"]) == {"msi", "nsis", "app", "dmg", "appimage", "deb", "rpm"}
    assert "bundled_app/**/*" in bundle["resources"]


def test_staged_backend_contains_runtime_entrypoint_and_config():
    staged = ROOT / "desktop_shell" / "src-tauri" / "bundled_app"
    assert (staged / "backend" / "main.py").is_file()
    assert (staged / "config" / "app_config.json").is_file()
