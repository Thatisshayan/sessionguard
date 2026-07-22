# Bundle Directory

This directory contains bundled dependencies for the SessionGuard desktop app.

## Required Files (for distribution builds)

Place the following in this directory before building the Tauri app:

### Python Runtime
- `python/python.exe` — Python 3.12 (embeddable package from python.org)
- `python/Lib/site-packages/` — pre-installed dependencies (use `pip install -t`)

### Tesseract OCR
- `tesseract/tesseract.exe` — Tesseract 5.x
- `tesseract/tessdata/` — language data files

### FFmpeg
- `ffmpeg/ffmpeg.exe` — FFmpeg binary

## Building with Bundled Dependencies

1. Download Python embeddable: https://www.python.org/ftp/python/3.12.4/python-3.12.4-embed-amd64.zip
2. Extract to `python/`
3. Install deps: `python/python.exe -m pip install -t python/Lib/site-packages -r ../../requirements.txt`
4. Download Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
5. Extract to `tesseract/`
6. Download FFmpeg: https://www.gyan.dev/ffmpeg/builds/
7. Extract to `ffmpeg/`
8. Run `cargo tauri build` from the desktop_shell directory

## Notes

- Total bundled size target: < 50MB compressed
- Python embeddable is ~10MB, Tesseract ~5MB, FFmpeg ~10MB
- The app will fall back to system-installed versions if bundled versions are not found
