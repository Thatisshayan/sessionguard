"""
backend/services/csv_parser.py
-------------------------------
Parses uploaded CSV files into sessions + events.

Supported formats (auto-detected):
  A) SPIN-LEVEL: one row per spin
     Required columns: date, bet_amount, win_amount, balance_after
     Optional: game_name, platform, event_type, timestamp

  B) SESSION-LEVEL: one row per session (summary)
     Required: date, game_name, start_balance, end_balance, total_bets, spins
     Optional: platform, notes, biggest_win, losing_streak

The parser returns a ParseResult dict. On success, the session and all
events are persisted to the database and insights/alerts are generated.

Maturity: Working Prototype
Future:   Add profile-based column mapping (V7), OCR-assisted repair (V8).
"""

import csv
import io
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import pandas as pd

from database.db import get_connection
from engines.insights_engine import generate_and_persist_insights
from engines.alerts_engine import generate_and_persist_alerts
from engines.review_queue_engine import get_queue_summary


# ── Column aliases — maps common external names to our canonical names ─────────
SPIN_ALIASES = {
    "bet":         "bet_amount",
    "stake":       "bet_amount",
    "wager":       "bet_amount",
    "bet_size":    "bet_amount",
    "win":         "win_amount",
    "payout":      "win_amount",
    "return":      "win_amount",
    "balance":     "balance_after",
    "bal":         "balance_after",
    "bal_after":   "balance_after",
    "type":        "event_type",
    "kind":        "event_type",
    "time":        "timestamp",
    "datetime":    "timestamp",
    "ts":          "timestamp",
    "game":        "game_name",
    "title":       "game_name",
    "casino":      "platform",
    "site":        "platform",
    "operator":    "platform",
    "confidence":  "confidence_score",
}

SESSION_ALIASES = {
    "start_bal":    "start_balance",
    "end_bal":      "end_balance",
    "opening_bal":  "start_balance",
    "closing_bal":  "end_balance",
    "bets":         "total_bets",
    "wagered":      "total_bets",
    "wins":         "total_wins",
    "returned":     "total_wins",
    "duration":     "duration_minutes",
    "minutes":      "duration_minutes",
    "game":         "game_name",
    "casino":       "platform",
    "site":         "platform",
    "biggest_w":    "biggest_win",
    "max_win":      "biggest_win",
    "streak":       "losing_streak",
    "loss_streak":  "losing_streak",
}

SPIN_REQUIRED    = {"bet_amount", "win_amount", "balance_after"}
SESSION_REQUIRED = {"start_balance", "end_balance", "total_bets", "spins"}


def _normalise_columns(df: pd.DataFrame, aliases: dict) -> pd.DataFrame:
    """Lowercase + strip all column names, then apply alias map."""
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df.rename(columns={k: v for k, v in aliases.items() if k in df.columns})


def _detect_format(df: pd.DataFrame) -> Optional[str]:
    """Return 'spin', 'session', or None if unrecognised."""
    cols = set(df.columns)
    if SPIN_REQUIRED.issubset(cols):
        return "spin"
    if SESSION_REQUIRED.issubset(cols):
        return "session"
    return None


def parse_csv_file(file_path: str, upload_id: int, session_id: int | None = None) -> dict:
    """
    Main entry point. Reads a CSV file, detects format, persists data.

    Returns:
        {
          "success": bool,
          "format": "spin" | "session" | None,
          "sessions_created": int,
          "events_created": int,
          "warnings": [...],
          "errors": [...],
          "session_ids": [...],
        }
    """
    result = {
        "success":          False,
        "format":           None,
        "sessions_created": 0,
        "events_created":   0,
        "warnings":         [],
        "errors":           [],
        "session_ids":      [],
    }

    path = Path(file_path)
    if not path.exists():
        result["errors"].append(f"File not found: {file_path}")
        return result

    # ── Load file ──────────────────────────────────────────────────────────────
    try:
        df = pd.read_csv(str(path))
    except Exception as e:
        result["errors"].append(f"Failed to read CSV: {e}")
        return result

    if df.empty:
        result["errors"].append("CSV file is empty.")
        return result

    df = _normalise_columns(df, {**SPIN_ALIASES, **SESSION_ALIASES})
    fmt = _detect_format(df)
    result["format"] = fmt

    if fmt is None:
        missing_spin    = SPIN_REQUIRED    - set(df.columns)
        missing_session = SESSION_REQUIRED - set(df.columns)
        result["errors"].append(
            f"Could not detect CSV format. "
            f"For spin-level data, missing: {missing_spin}. "
            f"For session-level data, missing: {missing_session}. "
            f"Found columns: {list(df.columns)}"
        )
        return result

    if fmt == "spin":
        return _parse_spin_level(df, upload_id, result, session_id)
    else:
        return _parse_session_level(df, upload_id, result)


# ── Spin-level parser ─────────────────────────────────────────────────────────

def _parse_spin_level(
    df: pd.DataFrame,
    upload_id: int,
    result: dict,
    session_id: int | None,
) -> dict:
    """
    One row per spin. Groups into one session (or links to existing session_id).
    """
    # Coerce numeric columns
    for col in ["bet_amount", "win_amount", "balance_after", "confidence_score"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Drop rows with missing required values
    before = len(df)
    df = df.dropna(subset=["bet_amount", "win_amount", "balance_after"])
    dropped = before - len(df)
    if dropped:
        result["warnings"].append(f"Dropped {dropped} rows with missing required values.")

    if df.empty:
        result["errors"].append("No valid spin rows after cleaning.")
        return result

    # ── Derive session metrics from spins ─────────────────────────────────────
    game_name  = str(df["game_name"].iloc[0]).strip()  if "game_name" in df.columns else "Unknown"
    platform   = str(df["platform"].iloc[0]).strip()   if "platform" in df.columns else "Unknown"
    date_val   = str(df["date"].iloc[0]).strip()[:10]  if "date" in df.columns else datetime.now().strftime("%Y-%m-%d")

    total_bets  = round(df["bet_amount"].sum(), 2)
    total_wins  = round(df["win_amount"].sum(), 2)
    start_bal   = round(float(df["balance_after"].iloc[0]) + float(df["bet_amount"].iloc[0]) - float(df["win_amount"].iloc[0]), 2)
    end_bal     = round(float(df["balance_after"].iloc[-1]), 2)
    net_result  = round(end_bal - start_bal, 2)
    rtp         = round(total_wins / total_bets * 100, 2) if total_bets > 0 else 0.0
    spins       = len(df)
    biggest_win = round(df["win_amount"].max(), 2)

    # Losing streak = max consecutive zero-win spins
    losing_streak = _calc_losing_streak(df["win_amount"].tolist())

    conn = get_connection()

    # ── Create or reuse session ───────────────────────────────────────────────
    if session_id:
        s_id = session_id
        result["warnings"].append(f"Events linked to existing session ID {session_id}.")
    else:
        cur = conn.execute(
            "INSERT INTO sessions (name, game_name, platform, date, start_balance, "
            "end_balance, total_bets, total_wins, net_result, rtp, spins, "
            "biggest_win, losing_streak, status, notes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'complete', ?)",
            (
                f"Imported — {game_name} ({date_val})",
                game_name, platform, date_val, start_bal,
                end_bal, total_bets, total_wins, net_result, rtp,
                spins, biggest_win, losing_streak,
                f"Auto-imported from CSV upload #{upload_id}",
            )
        )
        s_id = cur.lastrowid
        result["sessions_created"] += 1
        result["session_ids"].append(s_id)

    # ── Link upload to session ────────────────────────────────────────────────
    conn.execute("UPDATE uploads SET session_id = ?, status = 'complete' WHERE id = ?",
                 (s_id, upload_id))

    # ── Insert events ─────────────────────────────────────────────────────────
    base_time = datetime.now() - timedelta(days=1)
    event_count = 0

    for i, row in df.iterrows():
        ts = str(row.get("timestamp", "")).strip()
        if not ts or ts == "nan":
            ts = (base_time + timedelta(seconds=int(i) * 30)).isoformat()

        confidence = float(row.get("confidence_score", 1.0))
        confidence = max(0.0, min(1.0, confidence))

        conn.execute(
            "INSERT INTO events (session_id, timestamp, event_type, bet_amount, "
            "win_amount, balance_after, confidence_score, source) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, 'csv')",
            (
                s_id,
                ts,
                str(row.get("event_type", "spin")),
                float(row["bet_amount"]),
                float(row["win_amount"]),
                float(row["balance_after"]),
                confidence,
            )
        )
        event_count += 1

        # Flag low-confidence events for review
        if confidence < 0.80:
            conn.execute(
                "INSERT INTO review_items (session_id, reason, status) VALUES (?, ?, 'pending')",
                (s_id, f"Low confidence ({confidence:.2f}) on row {i + 1} — win ${float(row['win_amount']):.2f}")
            )

    conn.commit()
    conn.close()

    result["events_created"] = event_count

    # ── Generate insights + alerts ────────────────────────────────────────────
    generate_and_persist_insights(s_id)
    generate_and_persist_alerts(s_id)

    result["success"] = True
    return result


# ── Session-level parser ──────────────────────────────────────────────────────

def _parse_session_level(df: pd.DataFrame, upload_id: int, result: dict) -> dict:
    """One row per session. Creates multiple sessions from one CSV."""
    numeric_cols = [
        "start_balance", "end_balance", "total_bets", "total_wins",
        "spins", "biggest_win", "losing_streak", "duration_minutes",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    conn = get_connection()

    for _, row in df.iterrows():
        game_name = str(row.get("game_name", "Unknown")).strip()
        platform  = str(row.get("platform", "Unknown")).strip()
        date_val  = str(row.get("date", datetime.now().strftime("%Y-%m-%d"))).strip()[:10]
        start_bal = float(row.get("start_balance", 0))
        end_bal   = float(row.get("end_balance", 0))
        total_bets = float(row.get("total_bets", 0))
        total_wins = float(row.get("total_wins", 0))
        spins      = int(row.get("spins", 0))
        net_result = round(end_bal - start_bal, 2)
        rtp        = round(total_wins / total_bets * 100, 2) if total_bets > 0 else 0.0
        biggest_win   = float(row.get("biggest_win", 0))
        losing_streak = int(row.get("losing_streak", 0))
        duration      = int(row.get("duration_minutes", 0))
        notes         = str(row.get("notes", f"Imported from CSV upload #{upload_id}")).strip()

        cur = conn.execute(
            "INSERT INTO sessions (name, game_name, platform, date, duration_minutes, "
            "start_balance, end_balance, total_bets, total_wins, net_result, rtp, spins, "
            "biggest_win, losing_streak, status, notes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'complete', ?)",
            (
                f"Imported — {game_name} ({date_val})",
                game_name, platform, date_val, duration,
                start_bal, end_bal, total_bets, total_wins,
                net_result, rtp, spins, biggest_win, losing_streak, notes,
            )
        )
        s_id = cur.lastrowid
        result["sessions_created"] += 1
        result["session_ids"].append(s_id)

        generate_and_persist_insights(s_id)
        generate_and_persist_alerts(s_id)

    conn.execute("UPDATE uploads SET status = 'complete' WHERE id = ?", (upload_id,))
    conn.commit()
    conn.close()

    result["success"] = True
    return result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _calc_losing_streak(wins: list) -> int:
    """Return the longest consecutive losing (zero-win) streak."""
    max_streak = current = 0
    for w in wins:
        if w == 0:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak


def generate_csv_template(format_type: str = "spin") -> str:
    """
    Return a CSV template string so users know what column names to use.
    format_type: 'spin' | 'session'
    """
    if format_type == "session":
        return (
            "date,game_name,platform,start_balance,end_balance,total_bets,"
            "total_wins,spins,biggest_win,losing_streak,duration_minutes,notes\n"
            "2024-01-15,Book of Dead,BetMGM,500.00,423.50,1250.00,1173.50,"
            "250,87.50,12,90,Test session\n"
        )
    # spin-level default
    return (
        "date,game_name,platform,timestamp,event_type,bet_amount,win_amount,balance_after\n"
        "2024-01-15,Book of Dead,BetMGM,2024-01-15T14:00:00,spin,1.00,0.00,499.00\n"
        "2024-01-15,Book of Dead,BetMGM,2024-01-15T14:00:30,spin,1.00,2.50,500.50\n"
        "2024-01-15,Book of Dead,BetMGM,2024-01-15T14:01:00,spin,1.00,0.00,499.50\n"
    )
