"""
database/db.py
--------------
SQLite bootstrap, schema creation, and demo seeder.
Single source of truth for all table definitions.

Maturity: Working Prototype
Future:   Replace sqlite3 with asyncpg + Alembic for PostgreSQL/SaaS path.
"""

import os
import sqlite3
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH  = BASE_DIR / "config" / "sessionguard.db"


def get_connection():
    """Get a database connection. Uses SQLCipher if encryption is configured."""
    from database.encryption import get_encryption_config, create_encrypted_connection, SQLCIPHER_AVAILABLE

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db_path_str = str(DB_PATH)
    encryption = get_encryption_config()

    if encryption and SQLCIPHER_AVAILABLE:
        password = encryption.get("password") or os.getenv("SG_DB_PASSWORD", "")
        if password:
            return create_encrypted_connection(db_path_str, password)

    # Fallback: plain SQLite
    conn = sqlite3.connect(db_path_str, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT    NOT NULL,
    game_name        TEXT    NOT NULL,
    platform         TEXT    NOT NULL,
    date             TEXT    NOT NULL,
    duration_minutes INTEGER DEFAULT 0,
    start_balance    REAL    NOT NULL,
    end_balance      REAL    NOT NULL,
    total_bets       REAL    DEFAULT 0,
    total_wins       REAL    DEFAULT 0,
    net_result       REAL    DEFAULT 0,
    rtp              REAL    DEFAULT 0,
    spins            INTEGER DEFAULT 0,
    biggest_win      REAL    DEFAULT 0,
    biggest_loss     REAL    DEFAULT 0,
    losing_streak    INTEGER DEFAULT 0,
    status           TEXT    DEFAULT 'complete',
    notes            TEXT    DEFAULT '',
    created_at       TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS events (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id       INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    timestamp        TEXT    NOT NULL,
    event_type       TEXT    NOT NULL,
    bet_amount       REAL    DEFAULT 0,
    win_amount       REAL    DEFAULT 0,
    balance_after    REAL    DEFAULT 0,
    confidence_score REAL    DEFAULT 1.0,
    source           TEXT    DEFAULT 'manual',
    created_at       TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS uploads (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
    filename      TEXT    NOT NULL,
    file_type     TEXT    NOT NULL,
    file_path     TEXT    NOT NULL,
    status        TEXT    DEFAULT 'pending',
    error_message TEXT    DEFAULT '',
    created_at    TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS profiles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    game_name   TEXT    NOT NULL,
    platform    TEXT    NOT NULL,
    roi_config  TEXT    DEFAULT '{}',
    alert_rules TEXT    DEFAULT '{}',
    created_at  TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS insights (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    category   TEXT    NOT NULL,
    severity   TEXT    DEFAULT 'info',
    text       TEXT    NOT NULL,
    created_at TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS alerts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    rule         TEXT    NOT NULL,
    message      TEXT    NOT NULL,
    severity     TEXT    DEFAULT 'warning',
    acknowledged INTEGER DEFAULT 0,
    created_at   TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS review_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    event_id        INTEGER REFERENCES events(id) ON DELETE CASCADE,
    reason          TEXT    NOT NULL,
    status          TEXT    DEFAULT 'pending',
    corrected_value TEXT    DEFAULT '',
    reviewed_at     TEXT    DEFAULT '',
    created_at      TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS exports (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
    format     TEXT    NOT NULL,
    file_path  TEXT    NOT NULL,
    created_at TEXT    DEFAULT (datetime('now'))
);
"""


def init_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    print(f"[DB] Initialized at {DB_PATH}")


# ── Seeder ────────────────────────────────────────────────────────────────────
GAMES     = ["Book of Dead", "Gates of Olympus", "Sweet Bonanza", "Starburst", "Wolf Gold"]
PLATFORMS = ["BetMGM", "DraftKings", "FanDuel", "Bet365", "PokerStars Casino"]


def _random_session(i: int) -> dict:
    game      = random.choice(GAMES)
    platform  = random.choice(PLATFORMS)
    date      = (datetime.now() - timedelta(days=random.randint(1, 90))).strftime("%Y-%m-%d")
    duration  = random.randint(15, 180)
    start_bal = round(random.uniform(100, 1000), 2)
    spins     = random.randint(50, 500)
    bet_size  = round(random.uniform(0.20, 5.00), 2)
    total_bets = round(spins * bet_size, 2)
    rtp        = random.uniform(78, 108)
    total_wins = round(total_bets * rtp / 100, 2)
    net_result = round(total_wins - total_bets, 2)
    end_bal    = round(start_bal + net_result, 2)
    biggest_win   = round(bet_size * random.uniform(5, 50), 2)
    biggest_loss  = round(bet_size * random.randint(1, 10), 2)
    losing_streak = random.randint(0, 25)
    status = "flagged" if (rtp < 85 or losing_streak > 15) else "complete"

    return dict(
        name=f"Session {i+1} — {game}",
        game_name=game, platform=platform, date=date,
        duration_minutes=duration, start_balance=start_bal,
        end_balance=end_bal, total_bets=total_bets, total_wins=total_wins,
        net_result=net_result, rtp=round(rtp, 2), spins=spins,
        biggest_win=biggest_win, biggest_loss=biggest_loss,
        losing_streak=losing_streak, status=status, notes="",
    )


def _generate_events(session_id: int, session: dict, count: int = 20) -> list:
    events  = []
    balance = session["start_balance"]
    t0      = datetime.now() - timedelta(days=random.randint(1, 90))
    bet     = round(session["total_bets"] / max(session["spins"], 1), 2)

    for i in range(count):
        roll = random.random()
        win  = 0.0
        if roll > 0.55:
            multiplier = random.choice([0.5, 1.0, 2.0, 5.0, 10.0, 25.0])
            win = round(bet * multiplier, 2)

        balance = round(balance - bet + win, 2)
        events.append(dict(
            session_id=session_id,
            timestamp=(t0 + timedelta(minutes=i * 2)).isoformat(),
            event_type="spin", bet_amount=bet, win_amount=win,
            balance_after=balance,
            confidence_score=round(random.uniform(0.55, 1.0), 2),
            source="csv",
        ))
    return events


def _generate_insights(session_id: int, s: dict) -> list:
    out = []
    if s["rtp"] < 85:
        out.append(dict(session_id=session_id, category="performance", severity="critical",
            text=f"RTP of {s['rtp']}% is critically low. Net loss ${abs(s['net_result']):.2f} "
                 f"over {s['spins']} spins."))
    elif s["rtp"] < 96:
        out.append(dict(session_id=session_id, category="performance", severity="warning",
            text=f"RTP of {s['rtp']}% is below average. Review bet sizing."))
    else:
        out.append(dict(session_id=session_id, category="performance", severity="info",
            text=f"Solid session — RTP {s['rtp']}%, net result ${s['net_result']:.2f}."))

    if s["losing_streak"] > 15:
        out.append(dict(session_id=session_id, category="risk", severity="critical",
            text=f"Losing streak of {s['losing_streak']} spins — high variance risk period."))
    elif s["losing_streak"] > 8:
        out.append(dict(session_id=session_id, category="risk", severity="warning",
            text=f"Losing streak of {s['losing_streak']} spins detected."))

    if s["biggest_win"] > s["total_bets"] * 0.25:
        out.append(dict(session_id=session_id, category="behavior", severity="info",
            text=f"Largest win ${s['biggest_win']:.2f} was a significant session event."))

    return out


def _generate_alerts(session_id: int, s: dict) -> list:
    out = []
    if s["rtp"] < 85:
        out.append(dict(session_id=session_id, rule="rtp_critical",
            message=f"RTP {s['rtp']}% below critical threshold of 85%.",
            severity="critical", acknowledged=0))
    if s["net_result"] < -200:
        out.append(dict(session_id=session_id, rule="large_loss",
            message=f"Net loss ${abs(s['net_result']):.2f} exceeds $200 threshold.",
            severity="warning", acknowledged=0))
    if s["losing_streak"] > 15:
        out.append(dict(session_id=session_id, rule="long_losing_streak",
            message=f"Streak of {s['losing_streak']} consecutive losses flagged.",
            severity="critical", acknowledged=0))
    return out


def _generate_review_items(session_id: int, events: list, event_ids: list) -> list:
    out = []
    for i, ev in enumerate(events):
        if ev["confidence_score"] < 0.80:
            out.append(dict(
                session_id=session_id,
                event_id=event_ids[i] if i < len(event_ids) else None,
                reason=f"OCR confidence {ev['confidence_score']:.2f} — "
                       f"win amount ${ev['win_amount']:.2f} may be inaccurate.",
                status="pending", corrected_value="", reviewed_at="",
            ))
    return out


def seed_demo_data(force: bool = False):
    """Populate DB with realistic casino/slot demo data."""
    conn = get_connection()
    existing = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]

    if existing > 0 and not force:
        print(f"[DB] Seed skipped — {existing} sessions already exist.")
        conn.close()
        return

    if force:
        conn.executescript("""
            DELETE FROM review_items; DELETE FROM exports; DELETE FROM alerts;
            DELETE FROM insights; DELETE FROM events; DELETE FROM uploads;
            DELETE FROM sessions; DELETE FROM profiles;
        """)

    random.seed(42)

    # Default profiles
    conn.executemany(
        "INSERT OR IGNORE INTO profiles (name, game_name, platform, roi_config, alert_rules) "
        "VALUES (:name, :game_name, :platform, :roi_config, :alert_rules)",
        [
            dict(name="Generic Slot", game_name="Generic", platform="Generic",
                 roi_config=json.dumps({"balance_region": [10,10,200,50],
                                        "bet_region": [10,60,150,30],
                                        "win_region": [10,100,200,50]}),
                 alert_rules=json.dumps({"rtp_warning":96,"rtp_critical":85,
                                         "max_loss":200,"streak_warning":8,
                                         "streak_critical":15})),
            dict(name="Book of Dead", game_name="Book of Dead", platform="Generic",
                 roi_config=json.dumps({"balance_region": [15,15,210,45],
                                        "bet_region": [15,65,155,35],
                                        "win_region": [15,105,210,55]}),
                 alert_rules=json.dumps({"rtp_warning":94,"rtp_critical":84,
                                         "max_loss":150,"streak_warning":10,
                                         "streak_critical":20})),
        ]
    )

    for i in range(12):
        s = _random_session(i)
        cur = conn.execute(
            "INSERT INTO sessions (name,game_name,platform,date,duration_minutes,"
            "start_balance,end_balance,total_bets,total_wins,net_result,rtp,spins,"
            "biggest_win,biggest_loss,losing_streak,status,notes) VALUES "
            "(:name,:game_name,:platform,:date,:duration_minutes,:start_balance,"
            ":end_balance,:total_bets,:total_wins,:net_result,:rtp,:spins,"
            ":biggest_win,:biggest_loss,:losing_streak,:status,:notes)", s)
        sid = cur.lastrowid

        events = _generate_events(sid, s)
        event_ids = []
        for ev in events:
            c = conn.execute(
                "INSERT INTO events (session_id,timestamp,event_type,bet_amount,"
                "win_amount,balance_after,confidence_score,source) VALUES "
                "(:session_id,:timestamp,:event_type,:bet_amount,:win_amount,"
                ":balance_after,:confidence_score,:source)", ev)
            event_ids.append(c.lastrowid)

        for ins in _generate_insights(sid, s):
            conn.execute("INSERT INTO insights (session_id,category,severity,text) "
                         "VALUES (:session_id,:category,:severity,:text)", ins)

        for al in _generate_alerts(sid, s):
            conn.execute("INSERT INTO alerts (session_id,rule,message,severity,acknowledged) "
                         "VALUES (:session_id,:rule,:message,:severity,:acknowledged)", al)

        for ri in _generate_review_items(sid, events, event_ids):
            conn.execute("INSERT INTO review_items (session_id,event_id,reason,status,"
                         "corrected_value,reviewed_at) VALUES "
                         "(:session_id,:event_id,:reason,:status,:corrected_value,:reviewed_at)", ri)

    conn.commit()
    conn.close()
    print("[DB] Seeded 12 sessions with events, insights, alerts, and review items.")


if __name__ == "__main__":
    init_db()
    seed_demo_data()


# ── Phase 3 schema additions ──────────────────────────────────────────────────
SCHEMA_V2_SQL = """
CREATE TABLE IF NOT EXISTS live_runs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id       INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    mode             TEXT    NOT NULL DEFAULT 'mock',
    status           TEXT    NOT NULL DEFAULT 'stopped',
    event_index      INTEGER DEFAULT 0,
    tick_interval    REAL    DEFAULT 2.0,
    autosave_enabled INTEGER DEFAULT 1,
    started_at       TEXT    DEFAULT (datetime('now')),
    stopped_at       TEXT    DEFAULT '',
    metadata         TEXT    DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS live_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id     INTEGER NOT NULL REFERENCES live_runs(id) ON DELETE CASCADE,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    event_type TEXT    NOT NULL,
    payload    TEXT    NOT NULL DEFAULT '{}',
    created_at TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS live_checkpoints (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id     INTEGER NOT NULL REFERENCES live_runs(id) ON DELETE CASCADE,
    session_id INTEGER NOT NULL,
    data       TEXT    NOT NULL DEFAULT '{}',
    created_at TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ocr_results (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id       INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    upload_id        INTEGER REFERENCES uploads(id) ON DELETE CASCADE,
    frame_path       TEXT    NOT NULL,
    balance_value    REAL,
    bet_value        REAL,
    win_value        REAL,
    raw_text         TEXT    DEFAULT '',
    confidence_avg   REAL    DEFAULT 0,
    confidence_bal   REAL    DEFAULT 0,
    confidence_bet   REAL    DEFAULT 0,
    confidence_win   REAL    DEFAULT 0,
    flagged          INTEGER DEFAULT 0,
    created_at       TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS video_jobs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id       INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    upload_id        INTEGER REFERENCES uploads(id) ON DELETE CASCADE,
    status           TEXT    NOT NULL DEFAULT 'pending',
    frames_extracted INTEGER DEFAULT 0,
    frames_ocr_done  INTEGER DEFAULT 0,
    scene_changes    INTEGER DEFAULT 0,
    events_built     INTEGER DEFAULT 0,
    error_message    TEXT    DEFAULT '',
    started_at       TEXT    DEFAULT '',
    completed_at     TEXT    DEFAULT '',
    output_dir       TEXT    DEFAULT '',
    created_at       TEXT    DEFAULT (datetime('now'))
);
"""


def init_db_v2():
    """Apply Phase 3 schema additions."""
    conn = get_connection()
    conn.executescript(SCHEMA_V2_SQL)
    conn.commit()
    conn.close()
    print("[DB] Phase 3 schema applied.")


# ── Phase 4 SaaS schema ───────────────────────────────────────────────────────
SCHEMA_V3_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    email           TEXT    NOT NULL UNIQUE,
    username        TEXT    NOT NULL UNIQUE,
    hashed_password TEXT    NOT NULL,
    role            TEXT    NOT NULL DEFAULT 'user',
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    DEFAULT (datetime('now')),
    last_login      TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    description TEXT    DEFAULT '',
    owner_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tags        TEXT    DEFAULT '[]',
    created_at  TEXT    DEFAULT (datetime('now')),
    updated_at  TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS project_members (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role       TEXT    NOT NULL DEFAULT 'viewer',
    joined_at  TEXT    DEFAULT (datetime('now')),
    UNIQUE(project_id, user_id)
);

CREATE TABLE IF NOT EXISTS session_projects (
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    added_at   TEXT    DEFAULT (datetime('now')),
    PRIMARY KEY (session_id, project_id)
);

CREATE TABLE IF NOT EXISTS jobs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type      TEXT    NOT NULL,
    status        TEXT    NOT NULL DEFAULT 'pending',
    session_id    INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
    upload_id     INTEGER REFERENCES uploads(id) ON DELETE SET NULL,
    user_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,
    payload       TEXT    DEFAULT '{}',
    result        TEXT    DEFAULT '{}',
    error_message TEXT    DEFAULT '',
    progress      INTEGER DEFAULT 0,
    max_progress  INTEGER DEFAULT 100,
    started_at    TEXT    DEFAULT '',
    completed_at  TEXT    DEFAULT '',
    created_at    TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT    NOT NULL UNIQUE,
    expires_at TEXT    NOT NULL,
    created_at TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action     TEXT    NOT NULL,
    resource   TEXT    NOT NULL DEFAULT '',
    detail     TEXT    DEFAULT '{}',
    ip_address TEXT    DEFAULT '',
    created_at TEXT    DEFAULT (datetime('now'))
);
"""


def init_db_v3():
    """Apply Phase 4 SaaS schema."""
    conn = get_connection()
    conn.executescript(SCHEMA_V3_SQL)
    conn.commit()
    conn.close()
    print("[DB] Phase 4 SaaS schema applied.")


def seed_demo_user():
    """Create a demo user for local development."""
    from backend.auth.service import hash_password
    conn = get_connection()
    existing = conn.execute("SELECT id FROM users WHERE email=?",
                            ("demo@sessionguard.local",)).fetchone()
    if existing:
        conn.close()
        return
    conn.execute(
        "INSERT INTO users (email, username, hashed_password, role) VALUES (?,?,?,?)",
        ("demo@sessionguard.local", "demo",
         hash_password("demo123"), "admin")
    )
    conn.commit()
    conn.close()
    print("[DB] Demo user created: demo@sessionguard.local / demo123")


# ── Phase 5 schema additions ──────────────────────────────────────────────────
SCHEMA_V4_SQL = """
CREATE TABLE IF NOT EXISTS session_notes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    note       TEXT    NOT NULL,
    version    INTEGER NOT NULL DEFAULT 1,
    created_at TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS system_settings (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
);
"""


def init_db_v4():
    """Apply Phase 5 schema additions."""
    conn = get_connection()
    conn.executescript(SCHEMA_V4_SQL)
    conn.commit()
    conn.close()
    print("[DB] Phase 5 schema applied.")


def get_db_path() -> str:
    """Return the absolute path to the SQLite database file."""
    import json
    from pathlib import Path
    config_path = Path(__file__).resolve().parent.parent / "config" / "app_config.json"
    try:
        cfg = json.loads(config_path.read_text())
        rel = cfg.get("database", {}).get("path", "config/sessionguard.db")
        db  = Path(__file__).resolve().parent.parent / rel
        return str(db)
    except Exception:
        return str(Path(__file__).resolve().parent.parent / "config" / "sessionguard.db")


# ── V11 + V12 schema ─────────────────────────────────────────────────────────
SCHEMA_V5_SQL = """
CREATE TABLE IF NOT EXISTS session_tags (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    tag        TEXT    NOT NULL,
    created_at TEXT    DEFAULT (datetime('now')),
    UNIQUE(session_id, tag)
);

CREATE TABLE IF NOT EXISTS session_comments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    parent_id  INTEGER REFERENCES session_comments(id) ON DELETE CASCADE,
    body       TEXT    NOT NULL,
    created_at TEXT    DEFAULT (datetime('now')),
    updated_at TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS activity_feed (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    session_id  INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
    project_id  INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    action_type TEXT    NOT NULL,
    detail      TEXT    DEFAULT '{}',
    created_at  TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS review_assignments (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    review_item_id INTEGER NOT NULL REFERENCES review_items(id) ON DELETE CASCADE,
    assigned_to    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assigned_by    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    status         TEXT    NOT NULL DEFAULT 'open',
    created_at     TEXT    DEFAULT (datetime('now')),
    UNIQUE(review_item_id, assigned_to)
);

CREATE TABLE IF NOT EXISTS session_clusters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_label   TEXT    NOT NULL,
    session_id      INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    similarity_score REAL   DEFAULT 0,
    computed_at     TEXT    DEFAULT (datetime('now')),
    UNIQUE(cluster_label, session_id)
);

CREATE TABLE IF NOT EXISTS ai_insights (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    insight_type TEXT   NOT NULL DEFAULT 'narrative',
    prompt_hash TEXT    NOT NULL DEFAULT '',
    content     TEXT    NOT NULL,
    model       TEXT    NOT NULL DEFAULT 'claude-sonnet-4-20250514',
    tokens_used INTEGER DEFAULT 0,
    created_at  TEXT    DEFAULT (datetime('now'))
);
"""


def init_db_v5():
    """Apply V11 + V12 + V13 schema."""
    conn = get_connection()
    conn.executescript(SCHEMA_V5_SQL)
    conn.commit()
    conn.close()
    print("[DB] V11/V12/V13 schema applied.")


# ── Phase 1 (A6): composite indexes on hot query paths ─────────────────────────
SCHEMA_V6_SQL = """
CREATE INDEX IF NOT EXISTS idx_events_session_timestamp    ON events(session_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_live_events_run_id           ON live_events(run_id, id);
CREATE INDEX IF NOT EXISTS idx_uploads_session_id           ON uploads(session_id);
CREATE INDEX IF NOT EXISTS idx_insights_session_id          ON insights(session_id);
CREATE INDEX IF NOT EXISTS idx_alerts_session_id            ON alerts(session_id);
CREATE INDEX IF NOT EXISTS idx_review_items_session_id      ON review_items(session_id);
CREATE INDEX IF NOT EXISTS idx_ocr_results_session_id       ON ocr_results(session_id);
CREATE INDEX IF NOT EXISTS idx_video_jobs_session_id        ON video_jobs(session_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash          ON refresh_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id            ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_insights_session_id       ON ai_insights(session_id);
"""


def init_db_v6():
    """Apply Phase 1 (A6) composite/FK indexes — idempotent, safe to re-run."""
    conn = get_connection()
    conn.executescript(SCHEMA_V6_SQL)
    conn.commit()
    conn.close()
    print("[DB] V6 indexes applied.")


# ── Phase 2 (A7): job retry tracking column ───────────────────────────────────
SCHEMA_V7_SQL = """
ALTER TABLE jobs ADD COLUMN attempt INTEGER DEFAULT 0;
"""


def init_db_v7():
    """Apply Phase 2 (A7) job retry tracking — idempotent, safe to re-run."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_V7_SQL)
        conn.commit()
        print("[DB] V7 job attempt column added.")
    except Exception as e:
        # Column may already exist
        if "duplicate column name" not in str(e).lower():
            raise
    finally:
        conn.close()


# ── Phase 4 (D3): prompt versioning + A/B ────────────────────────────────────
SCHEMA_V8_SQL = """
CREATE TABLE IF NOT EXISTS prompt_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    version INTEGER NOT NULL,
    system_prompt TEXT NOT NULL,
    model TEXT DEFAULT 'claude-sonnet-4-6',
    temperature REAL DEFAULT 1.0,
    max_tokens INTEGER DEFAULT 1024,
    is_active INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(name, version)
);

CREATE TABLE IF NOT EXISTS ab_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    prompt_a_id INTEGER NOT NULL,
    prompt_b_id INTEGER NOT NULL,
    winner TEXT,
    metrics TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def init_db_v8():
    """Apply Phase 4 (D3) prompt versioning tables — idempotent."""
    conn = get_connection()
    conn.executescript(SCHEMA_V8_SQL)
    conn.commit()
    conn.close()
    print("[DB] V8 prompt versioning tables applied.")

# ── Phase 5 (D6): AI cost tracking ────────────────────────────────────────────
SCHEMA_V9_SQL = """
CREATE TABLE IF NOT EXISTS ai_cost_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    model TEXT NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def init_db_v9():
    """Apply Phase 5 (D6) AI cost tracking — idempotent."""
    conn = get_connection()
    conn.executescript(SCHEMA_V9_SQL)
    conn.commit()
    conn.close()
    print("[DB] V9 AI cost tracking applied.")
