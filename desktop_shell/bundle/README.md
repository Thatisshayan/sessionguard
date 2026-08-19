# Bundle Directory

This directory holds optional desktop runtime assets that are staged into
`desktop_shell/src-tauri/bundled_app/` before packaging.

Current packaged-release support is Windows-only. The release workflow hydrates
the Windows Python runtime in CI, and local builds can do the same with the
PowerShell scripts in `scripts/bundle/`.

## Runtime Folder Contract

The desktop launcher and staging script currently recognize these folders:

- `python_win/`
- `tesseract_win/`
- `ffmpeg_win/`

Required entrypoints inside those folders:

- `python_win/python.exe`
- `tesseract_win/tesseract.exe`
- `ffmpeg_win/ffmpeg.exe`

## Local Windows Bundling

From the repo root:

```powershell
pwsh -File scripts/bundle/bundle_python_win.ps1
pwsh -File scripts/bundle/bundle_tesseract_win.ps1
pwsh -File scripts/bundle/bundle_tessdata.ps1
pwsh -File scripts/bundle/bundle_ffmpeg_win.ps1
```

Then build the installer:

```powershell
cd desktop_shell
$env:SESSIONGUARD_REQUIRE_BUNDLED_PYTHON = "1"
npm run tauri:build
```

## CI Behavior

- Windows release builds require a valid bundled Python runtime.
- Smoke/dev paths can stage backend sources without a bundled Python runtime and
  rely on host `python` instead.
- macOS/Linux packaged releases are deferred until native runtime bundling is
  implemented for those platforms.
