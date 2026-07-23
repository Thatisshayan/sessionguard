"""Tests for AI cost tracking."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from engines.ai_insights_engine import _compute_cost, get_daily_cost


class TestComputeCost(unittest.TestCase):
    def test_nvidia_nemotron_cost(self):
        cost = _compute_cost("nvidia/llama-3.1-nemotron-70b-instruct", 1000, 500)
        # (1000 * 0.12 + 500 * 0.12) / 1_000_000 = 0.00018
        self.assertAlmostEqual(cost, 0.00018, places=6)

    def test_zero_tokens(self):
        cost = _compute_cost("nvidia/llama-3.1-nemotron-70b-instruct", 0, 0)
        self.assertEqual(cost, 0.0)

    def test_unknown_model_defaults(self):
        cost = _compute_cost("unknown-model", 1000, 1000)
        self.assertGreater(cost, 0)


class TestDailyCost(unittest.TestCase):
    def test_returns_dict(self):
        result = get_daily_cost()
        self.assertIn("calls_today", result)
        self.assertIn("cost_usd", result)
        self.assertIn("budget_usd", result)
        self.assertIn("budget_exceeded", result)


if __name__ == "__main__":
    unittest.main()