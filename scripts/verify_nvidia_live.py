"""
scripts/verify_nvidia_live.py
-----------------------------
Live verification for Revival 1.3 task B3 — "NVIDIA NIM live verification".

The mocked contract tests (tests/test_ai_insights_contract.py) pin the
transport/persistence/fallback contract entirely with mocks. This script
performs the one thing they intentionally cannot: a real call to
https://integrate.api.nvidia.com with a real NVIDIA_API_KEY.

What it asserts (mirrors TestAnalyseSessionWithAiContract but live):
  1. analyse_session_with_ai() returns source == "nvidia_ai" (not rule_based,
     not ollama_ai).
  2. ai_available is True and the active model matches NVIDIA_MODELS[0].
  3. AI insights are persisted to the insights table with the "[AI]" prefix.
  4. A cost row lands in ai_cost_log with input/output tokens > 0.

Safety:
  - Uses an ISOLATED throwaway database (SG_DATA_DIR -> temp dir), never the
    real sessionguard.db.
  - Requires NVIDIA_API_KEY in the environment; refuses to run without it.
  - One analysis call only (~1024 max output tokens, few-hundred input tokens).

Usage:
  $env:NVIDIA_API_KEY = "nvapi-..."   # or export NVIDIA_API_KEY=...
  python scripts/verify_nvidia_live.py

Requires R24 approval (paid NVIDIA NIM API, pay-per-token) from Shayan.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _seed_session_and_events(conn) -> int:
    """Insert one session + two events (mirrors tests' seeded_session fixture)."""
    conn.execute(
        "INSERT INTO sessions (name, game_name, platform, date, duration_minutes, "
        "start_balance, end_balance, net_result, rtp, spins, total_bets, biggest_win, "
        "losing_streak, status) "
        "VALUES ('Live B3 verification', 'Slot X', 'desktop', '2026-08-14', 60, 1000, 940, "
        "-60, 91, 100, 500, 25, 8, 'reviewed')"
    )
    conn.execute(
        "INSERT INTO events (session_id, event_type, timestamp, bet_amount, win_amount, "
        "balance_after, confidence_score) "
        "VALUES (1, 'spin', '2026-08-14T10:00:00', 5, 0, 995, 0.9)"
    )
    conn.execute(
        "INSERT INTO events (session_id, event_type, timestamp, bet_amount, win_amount, "
        "balance_after, confidence_score) "
        "VALUES (1, 'spin', '2026-08-14T10:01:00', 5, 25, 1015, 0.92)"
    )
    conn.commit()
    session_id = conn.execute("SELECT id FROM sessions").fetchone()["id"]
    return session_id


def main() -> int:
    api_key = os.getenv("NVIDIA_API_KEY", "").strip()
    if not api_key:
        print("ERROR: NVIDIA_API_KEY not set — refusing to run.")
        print("B3 live verification requires R24 approval + a real NVIDIA NIM key.")
        return 2

    # Isolated throwaway DB. SG_DATA_DIR must be set before `database.db` is
    # imported so BASE_DIR/DB_PATH resolve to the temp dir. This is a fresh
    # process, so a plain env var is enough — no importlib reload needed.
    temp_dir = Path(tempfile.mkdtemp(prefix="sg-b3-live-"))
    os.environ["SG_DATA_DIR"] = str(temp_dir)

    import database.db as db
    from engines import ai_insights_engine as ai

    for init in ("init_db", "init_db_v2", "init_db_v3", "init_db_v4",
                 "init_db_v5", "init_db_v6", "init_db_v7", "init_db_v8",
                 "init_db_v9"):
        getattr(db, init)()

    conn = db.get_connection()
    session_id = _seed_session_and_events(conn)
    conn.close()

    print(f"[B3] Live NVIDIA NIM verification (session {session_id})")
    print(f"[B3] Model: {ai.NVIDIA_MODELS[0]}  |  Endpoint: {ai.API_URL}")
    print("[B3] Calling real NVIDIA API... (one analysis, ~1024 max tokens)")

    result = ai.analyse_session_with_ai(session_id)

    failures: list[str] = []

    if result.get("source") != "nvidia_ai":
        failures.append(f"source == {result.get('source')!r}, expected 'nvidia_ai'")
    if result.get("ai_available") is not True:
        failures.append(f"ai_available == {result.get('ai_available')!r}, expected True")
    if result.get("model") != ai.NVIDIA_MODELS[0]:
        failures.append(f"model == {result.get('model')!r}, expected {ai.NVIDIA_MODELS[0]}")
    if result.get("error"):
        failures.append(f"engine returned error: {result['error']}")

    conn = db.get_connection()
    ai_rows = conn.execute(
        "SELECT text FROM insights WHERE session_id=? AND text LIKE '[AI]%'",
        (session_id,)
    ).fetchall()
    cost_rows = conn.execute(
        "SELECT model, input_tokens, output_tokens, cost_usd FROM ai_cost_log"
    ).fetchall()
    conn.close()

    if not ai_rows:
        failures.append("no [AI] insights persisted to insights table")
    if not cost_rows:
        failures.append("no row landed in ai_cost_log")
    elif cost_rows[0]["input_tokens"] == 0 and cost_rows[0]["output_tokens"] == 0:
        failures.append("ai_cost_log row has zero tokens (usage not reported)")

    print(f"[B3] source={result.get('source')} model={result.get('model')} "
          f"risk={result.get('risk_level')}")
    print(f"[B3] headline: {result.get('headline')}")
    print(f"[B3] insights persisted: {len(ai_rows)}  cost rows: {len(cost_rows)}")
    if cost_rows:
        c = cost_rows[0]
        print(f"[B3] cost_log: model={c['model']} in={c['input_tokens']} "
              f"out={c['output_tokens']} cost=${c['cost_usd']:.6f}")

    if failures:
        print("\n[B3] FAIL:")
        for f in failures:
            print(f"  - {f}")
        print(f"[B3] DB left at {db.DB_PATH} for inspection.")
        return 1

    print("\n[B3] PASS — live NVIDIA NIM verification succeeded.")
    print("[B3] source == nvidia_ai, insights persisted, cost logged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())