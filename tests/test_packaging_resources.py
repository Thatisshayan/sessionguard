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


def test_packaging_version_matches_canonical_source_of_truth():
    """Closes the version-drift class (Revival 1.3 finding #12): every artifact
    must carry the same version as config/app_config.json so an installed app
    can never silently disagree with the bundled backend's /health report.
    """
    expected = json.loads((ROOT / "config" / "app_config.json").read_text())["version"]

    tauri_conf = json.loads((ROOT / "desktop_shell" / "src-tauri" / "tauri.conf.json").read_text())
    assert tauri_conf["package"]["version"] == expected, (
        f"tauri.conf.json version {tauri_conf['package']['version']!r} != "
        f"config/app_config.json {expected!r}"
    )

    package_json = json.loads((ROOT / "desktop_shell" / "package.json").read_text())
    assert package_json["version"] == expected, (
        f"desktop_shell/package.json version {package_json['version']!r} != "
        f"config/app_config.json {expected!r}"
    )

    cargo_toml = (ROOT / "desktop_shell" / "src-tauri" / "Cargo.toml").read_text()
    assert f'version = "{expected}"' in cargo_toml, (
        f"Cargo.toml does not declare version \"{expected}\""
    )


def test_resource_glob_matches_staged_backend_entrypoint():
    """The bundle resource glob must actually cover the staged backend dir —
    otherwise an installer built from this config would silently ship without
    the backend the desktop shell expects to launch (finding #13 regression).
    """
    glob = "bundled_app/**/*"
    staged_entrypoint = ROOT / "desktop_shell" / "src-tauri" / "bundled_app" / "backend" / "main.py"
    # The glob is relative to src-tauri; the staged dir lives under src-tauri,
    # so ``bundled_app/backend/main.py`` must be matched by ``bundled_app/**/*``.
    rel = staged_entrypoint.relative_to(ROOT / "desktop_shell" / "src-tauri")
    import fnmatch
    assert fnmatch.fnmatch(str(rel).replace("\\", "/"), glob), (
        f"staged entrypoint {rel} is not covered by resource glob {glob!r}"
    )
