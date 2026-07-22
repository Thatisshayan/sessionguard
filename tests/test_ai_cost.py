"""Tests for AI cost tracking."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from engines.ai_insights_engine import _compute_cost, get_daily_cost


class TestComputeCost(unittest.TestCase):
    def test_claude_sonnet_cost(self):
        cost = _compute_cost("claude-sonnet-4-6", 1000, 500)
        # (1000 * 3 + 500 * 15) / 1_000_000 = 0.0105
        self.assertAlmostEqual(cost, 0.0105, places=6)

    def test_zero_tokens(self):
        cost = _compute_cost("claude-sonnet-4-6", 0, 0)
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