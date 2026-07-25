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

import httpx

OLLAMA_BASE_URL = "http://localhost:11434"


# ── Shared async HTTP helpers ─────────────────────────────────────────────────

async def _async_http_post(url: str, json_data: dict, headers: dict | None = None, timeout: float = 60.0) -> dict:
    """Shared async HTTP POST returning parsed JSON. Wraps httpx errors in RuntimeError."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=json_data, headers=headers or {})
            if response.status_code >= 400:
                raise RuntimeError(f"HTTP error {response.status_code}: {response.text}")
            return response.json()
    except httpx.HTTPError as e:
        raise RuntimeError(f"HTTP request failed: {e}")


async def _async_http_get(url: str, timeout: float = 3.0) -> int | None:
    """Shared async HTTP GET returning status code, or None on failure."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            return response.status_code
    except Exception:
        return None
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


async def async_call_ollama(prompt: str, model: str | None = None, system_prompt: str | None = None) -> str:
    """Async HTTP version of call_ollama using shared httpx helpers."""
    model = model or DEFAULT_MODEL

    payload = {
        "model":   model,
        "prompt":  prompt,
        "stream":  False,
        "options": {"temperature": 0.7, "num_predict": 1024},
    }
    if system_prompt:
        payload["system"] = system_prompt

    try:
        body = await _async_http_post(f"{OLLAMA_BASE_URL}/api/generate", payload, timeout=120.0)
        return body.get("response", "")
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Ollama error: {e}")


async def async_call_ollama_json(prompt: str, model: str | None = None, system_prompt: str | None = None) -> dict:
    """Async HTTP version of call_ollama_json using httpx.AsyncClient."""
    raw = await async_call_ollama(prompt, model=model, system_prompt=system_prompt)

    text = raw.strip()
    if text.startswith("```"):
        lines = [l for l in text.split("\n") if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"error": "Could not parse Ollama response as JSON", "raw": raw[:500]}


async def async_is_ollama_available() -> bool:
    """Async version of is_ollama_available using shared httpx helpers."""
    status = await _async_http_get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3.0)
    return status == 200
