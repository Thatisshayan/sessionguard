"""Tests for engines/offline_ai.py — Ollama offline inference."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from unittest.mock import patch, MagicMock
from engines.offline_ai import is_ollama_available, list_available_models, call_ollama, call_ollama_json


class TestOllamaDetection(unittest.TestCase):
    @patch("engines.offline_ai.urllib.request.urlopen")
    def test_is_available_when_running(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        self.assertTrue(is_ollama_available())

    @patch("engines.offline_ai.urllib.request.urlopen", side_effect=ConnectionError)
    def test_is_not_available_when_down(self, mock_urlopen):
        self.assertFalse(is_ollama_available())


class TestListModels(unittest.TestCase):
    @patch("engines.offline_ai.urllib.request.urlopen")
    def test_lists_models(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = '{"models":[{"name":"llama3.2:latest"},{"name":"mistral:latest"}]}'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        models = list_available_models()
        self.assertEqual(models, ["llama3.2:latest", "mistral:latest"])

    @patch("engines.offline_ai.urllib.request.urlopen", side_effect=Exception)
    def test_returns_empty_on_error(self, mock_urlopen):
        self.assertEqual(list_available_models(), [])


class TestCallOllama(unittest.TestCase):
    @patch("engines.offline_ai.urllib.request.urlopen")
    def test_returns_response(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = '{"response":"Hello from Ollama"}'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = call_ollama("Say hello")
        self.assertEqual(result, "Hello from Ollama")

    @patch("engines.offline_ai.urllib.request.urlopen", side_effect=ConnectionError("refused"))
    def test_raises_on_connection_error(self, mock_urlopen):
        with self.assertRaises(RuntimeError):
            call_ollama("Say hello")


class TestCallOllamaJson(unittest.TestCase):
    @patch("engines.offline_ai.call_ollama")
    def test_parses_json(self, mock_call):
        mock_call.return_value = '{"headline":"test","risk_level":"low"}'
        result = call_ollama_json("Analyse this")
        self.assertEqual(result["headline"], "test")
        self.assertEqual(result["risk_level"], "low")

    @patch("engines.offline_ai.call_ollama")
    def test_handles_invalid_json(self, mock_call):
        mock_call.return_value = "This is not JSON at all"
        result = call_ollama_json("Analyse this")
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
