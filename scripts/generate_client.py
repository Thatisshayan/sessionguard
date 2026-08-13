#!/usr/bin/env python3
"""
scripts/generate_client.py
--------------------------
Exports OpenAPI schema from FastAPI backend and generates openapi.json
for frontend type-safe API client code generation.
"""

import sys
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from backend.main import app

def generate_openapi_spec():
    output_path = root / "frontend" / "openapi.json"
    spec = app.openapi()
    output_path.write_text(json.dumps(spec, indent=2))
    print(f"[OpenAPI] Exported OpenAPI specification to {output_path}")

if __name__ == "__main__":
    generate_openapi_spec()
