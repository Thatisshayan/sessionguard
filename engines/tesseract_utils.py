"""
engines/tesseract_utils.py — Shared Tesseract executable discovery.

Single source of truth for locating the Tesseract binary, used by the OCR
engine, the API health checks, and app startup. Resolution order:

    1. TESSERACT_CMD environment variable (when it points to an existing file)
    2. shutil.which("tesseract") — PATH lookup
    3. Standard Windows install locations (fallback)
"""

from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path


def find_tesseract() -> str | None:
    """Return the resolved tesseract executable path, or None if not found.

    Checks the ``TESSERACT_CMD`` environment variable, then ``PATH``, then the
    standard Windows install locations.
    """
    env_cmd = os.environ.get("TESSERACT_CMD")
    if env_cmd and Path(env_cmd).exists():
        return env_cmd

    path = shutil.which("tesseract")
    if path:
        return path

    if platform.system() == "Windows":
        candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for candidate in candidates:
            if Path(candidate).exists():
                return candidate
    return None
