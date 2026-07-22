"""
engines/offline_ai.py
---------------------
Offline AI inference via Ollama (local LLM server).
Falls back gracefully when Ollama is not available.
"""

from __future__ import annotations
import json
import urllib.request
import urllib.error

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2:latest"


def is_ollama_available() -> bool:
    """Check if Ollama is running and reachable."""
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def list_available_models() -> list[str]:
    """Return list of model names available in Ollama."""
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def call_ollama(prompt: str, model: str | None = None, system_prompt: str | None = None) -> str:
    """
    Call Ollama generate API with a prompt. Returns response text.
    Raises RuntimeError if Ollama is unreachable or returns an error.
    """
    model = model or DEFAULT_MODEL

    payload_dict = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 1024,
        }
    }
    if system_prompt:
        payload_dict["system"] = system_prompt

    payload = json.dumps(payload_dict).encode()

    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            body = json.loads(response.read())
            return body.get("response", "")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Ollama unreachable: {e}")
    except Exception as e:
        raise RuntimeError(f"Ollama error: {e}")


def call_ollama_json(prompt: str, model: str | None = None, system_prompt: str | None = None) -> dict:
    """
    Call Ollama and parse the response as JSON.
    Returns parsed dict on success, or {"error": ..., "raw": ...} on failure.
    """
    raw = call_ollama(prompt, model=model, system_prompt=system_prompt)

    # Try to extract JSON from the response (may be wrapped in markdown code blocks)
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (``` markers)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"error": "Could not parse Ollama response as JSON", "raw": raw[:500]}
