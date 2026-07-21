"""
engines/csv_import_engine.py - V14 CSV Import Engine
Original: ChatGPT | Reviewed: Claude (no changes needed - excellent code)
"""
import re, uuid as _uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
import pandas as pd
from database.db import get_connection

ColumnMapping = Dict[str, str]

MAPPING_ALIASES: Dict[str, Sequence[str]] = {
    "date":        ("date","time","datetime","timestamp","created_at","played_at","spin_time","transaction_date","session_date"),
    "bet":         ("bet","stake","wager","bet_amount","amount_bet","total_bet","spin_bet"),
    "win":         ("win","profit","payout","return","paid","win_amount","amount_won","net_win","result"),
    "balance":     ("balance","balance_after","ending_balance","cash_balance","bankroll","wallet","account_balance"),
    "spin_number": ("spin","spin_number","spin_no","spin_id","round","round_id","game_round"),
}

DATE_FORMATS: Sequence[str] = (
    "%Y-%m-%d","%Y-%m-%d %H:%M","%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M","%Y-%m-%dT%H:%M:%S",
    "%m/%d/%Y","%m/%d/%Y %H:%M","%m/%d/%Y %H:%M:%S",
    "%d/%m/%Y","%d/%m/%Y %H:%M","%d/%m/%Y %H:%M:%S",
    "%Y/%m/%d","%Y/%m/%d %H:%M","%Y/%m/%d %H:%M:%S",
    "%b %d %Y","%b %d, %Y","%b %d %Y %H:%M","%b %d, %Y %H:%M",
    "%B %d %Y","%B %d, %Y","%B %d %Y %H:%M","%B %d, %Y %H:%M",
)


def _read_csv(file_path: Path) -> pd.DataFrame:
    """Read CSV with encoding fallbacks."""
    path = Path(file_path)
    if not path.exists(): raise FileNotFoundError(f"CSV not found: {path}")
    last = None
    for enc in ("utf-8-sig","utf-8","cp1252","latin1"):
        try:
            df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding=enc)
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except Exception as e: last = e
    raise ValueError(f"Unable to read CSV: {last}")


def _norm(v: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(v or "").strip().lower())


def _suggest_column(columns: Sequence[str], aliases: Sequence[str]) -> str:
    nc = {c: _norm(c) for c in columns}
    na = [_norm(a) for a in aliases]
    for c, n in nc.items():
        if n in na: return c
    for c, n in nc.items():
        for a in na:
            if a and a in n: return c
    for c, n in nc.items():
        for a in na:
            if n and n in a: return c
    return ""


def _suggest_mapping(columns: Sequence[str]) -> Dict[str, str]:
    return {t: m for t, aliases in MAPPING_ALIASES.items() if (m := _suggest_column(columns, aliases))}


def preview_csv(file_path: Path) -> Dict[str, Any]:
    """Read CSV, detect columns, return first 10 rows + suggested mapping."""
    df  = _read_csv(Path(file_path))
    cols = [str(c) for c in df.columns]
    rows = [{c: (str(row.get(c,"")) if not pd.isna(row.get(c,"")) else "") for c in cols} for _, row in df.head(10).iterrows()]
    return {"columns": cols, "preview_rows": rows, "suggested_mapping": _suggest_mapping(cols)}


def _parse_date(v: Any) -> Optional[str]:
    raw = str(v or "").strip()
    if not raw: return None
    for fmt in DATE_FORMATS:
        try: return datetime.strptime(raw, fmt).isoformat()
        except ValueError: continue
    ts = pd.to_datetime(raw, errors="coerce")
    if pd.isna(ts): ts = pd.to_datetime(raw, errors="coerce", dayfirst=True)
    if pd.isna(ts): return None
    return ts.to_pydatetime().isoformat()


def _parse_number(v: Any) -> Optional[float]:
    raw = str(v or "").strip()
    if not raw: return None
    neg = raw.startswith("(") and raw.endswith(")")
    c   = re.sub(r"[,$£€\s()A-Za-z]", "", raw)
    if c in {"","-",".","+"}: return None
    try: n = float(c)
    except ValueError: return None
    if not (n == n): return None  # NaN guard
    return -abs(n) if neg else n


def import_csv(file_path: Path, mapping: ColumnMapping, session_id: str) -> Dict[str, Any]:
    """Apply column mapping, validate rows, insert events, return counts."""
    df   = _read_csv(Path(file_path))
    # Validate mapping
    warns: List[str] = []
    for f in ("date","bet","win","balance"):
        col = mapping.get(f)
        if not col: warns.append(f"Missing required mapping for {f}.")
        elif col not in df.columns: warns.append(f"Column for {f} not found: {col}")
    if warns: return {"imported":0, "skipped":len(df), "warnings":warns}

    conn = get_connection()
    imported = skipped = 0
    seen: set = set()
    row_warns: List[str] = []

    try:
        # Ensure events table exists
        conn.execute("""CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
            timestamp TEXT NOT NULL, event_type TEXT NOT NULL,
            bet_amount REAL, win_amount REAL, balance_after REAL,
            confidence_score REAL, source TEXT)""")
        conn.commit()
        ecols = {r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()}

        for idx, row in df.iterrows():
            rn = int(idx) + 2
            ts  = _parse_date(row.get(mapping["date"]))
            bet = _parse_number(row.get(mapping["bet"]))
            win = _parse_number(row.get(mapping["win"]))
            bal = _parse_number(row.get(mapping["balance"]))
            spin_col = mapping.get("spin_number")
            spin = str(row.get(spin_col,"")).strip() if spin_col and spin_col in row.index else None
            if not spin: spin = None

            if ts is None:  row_warns.append(f"Row {rn}: date not parseable."); skipped += 1; continue
            if bet is None: row_warns.append(f"Row {rn}: invalid bet."); skipped += 1; continue
            if bet < 0:     row_warns.append(f"Row {rn}: negative bet."); skipped += 1; continue
            if win is None: row_warns.append(f"Row {rn}: invalid win."); skipped += 1; continue
            if bal is None: row_warns.append(f"Row {rn}: invalid balance."); skipped += 1; continue

            key = (session_id, ts, round(bet,8), round(win,8), round(bal,8), str(spin or ""))
            if key in seen: row_warns.append(f"Row {rn}: duplicate skipped."); skipped += 1; continue
            seen.add(key)

            vals: Dict[str,Any] = {}
            if "session_id"      in ecols: vals["session_id"]      = session_id
            if "timestamp"       in ecols: vals["timestamp"]        = ts
            if "event_type"      in ecols: vals["event_type"]       = "spin"
            if "bet_amount"      in ecols: vals["bet_amount"]       = bet
            if "win_amount"      in ecols: vals["win_amount"]       = win
            if "balance_after"   in ecols: vals["balance_after"]    = bal
            if "confidence_score" in ecols: vals["confidence_score"] = 1.0
            if "source"          in ecols: vals["source"]           = "csv_import"
            if spin and "spin_number" in ecols: vals["spin_number"] = spin

            ks = list(vals.keys())
            conn.execute(f"INSERT INTO events ({','.join(ks)}) VALUES ({','.join('?'*len(ks))})", [vals[k] for k in ks])
            imported += 1

        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally: conn.close()

    return {"imported": imported, "skipped": skipped, "warnings": row_warns}
