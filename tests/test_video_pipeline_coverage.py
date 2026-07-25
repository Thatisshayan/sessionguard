"""Targeted coverage bump for engines/video_pipeline.py (Revival 1.3).
Covers edge cases not hit by existing tests: DB helpers, sequential dedup
first-frame hash, timestamp edge cases, checkpoint error path.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import engines.video_pipeline as vp


# ── _hamming_distance ─────────────────────────────────────────────────────────

class TestHammingDistance:
    def test_zero_for_identical(self):
        assert vp._hamming_distance(0b1010, 0b1010) == 0

    def test_counts_differing_bits(self):
        assert vp._hamming_distance(0b0000, 0b1111) == 4
        assert vp._hamming_distance(0b1010, 0b0101) == 4
        assert vp._hamming_distance(0b0001, 0b0010) == 2


# ── _phash with real image data ──────────────────────────────────────────────

class TestPhash:
    def test_returns_zero_for_missing_file(self, tmp_path):
        assert vp._phash(str(tmp_path / "missing.jpg")) == 0

    def test_returns_integer_hash_for_real_image(self, tmp_path):
        img_path = tmp_path / "test.png"
        arr = np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)
        import cv2
        cv2.imwrite(str(img_path), arr)
        h = vp._phash(str(img_path))
        assert isinstance(h, int)
        assert h > 0

    def test_similar_images_have_small_hamming_distance(self, tmp_path):
        img1_path = tmp_path / "img1.png"
        img2_path = tmp_path / "img2.png"
        base = np.full((64, 64, 3), 128, dtype=np.uint8)
        import cv2
        cv2.imwrite(str(img1_path), base)
        similar = base.copy()
        similar[0, 0] = [129, 129, 129]
        cv2.imwrite(str(img2_path), similar)
        h1 = vp._phash(str(img1_path))
        h2 = vp._phash(str(img2_path))
        assert vp._hamming_distance(h1, h2) < 5


# ── _checkpoint_job_chunk error path ─────────────────────────────────────────

class TestCheckpointJobChunk:
    def test_error_does_not_raise(self):
        vp._checkpoint_job_chunk(99999, 1)


# ── _get_job_progress_chunks ──────────────────────────────────────────────────

class TestGetJobProgressChunks:
    def test_returns_zero_for_missing_job(self, test_db):
        from database.db import init_db_v11
        init_db_v11()
        assert vp._get_job_progress_chunks(99999) == (0, 0)


# ── get_video_job ─────────────────────────────────────────────────────────────

class TestGetVideoJob:
    def test_returns_none_for_missing(self, test_db):
        assert vp.get_video_job(99999) is None

    def test_returns_dict_for_existing(self, test_db):
        import database.db as db
        conn = db.get_connection()
        conn.execute(
            "INSERT INTO sessions (name, game_name, platform, date, start_balance, end_balance, status) "
            "VALUES ('s', 'g', 'desktop', '2026-07-24', 1000, 940, 'reviewed')"
        )
        conn.execute("INSERT INTO uploads (session_id, filename, file_type, file_path) VALUES (1, 'v.mp4', 'video', '/tmp/v.mp4')")
        conn.execute(
            "INSERT INTO video_jobs (session_id, upload_id, status, started_at) "
            "VALUES (1, 1, 'running', '2026-07-24T10:00:00')"
        )
        conn.commit()
        job_id = conn.execute("SELECT id FROM video_jobs").fetchone()["id"]
        conn.close()
        job = vp.get_video_job(job_id)
        assert job is not None
        assert job["status"] == "running"


# ── get_video_jobs_for_session ────────────────────────────────────────────────

class TestGetVideoJobsForSession:
    def test_returns_empty_list_when_none(self, test_db):
        assert vp.get_video_jobs_for_session(99999) == []

    def test_returns_jobs_for_session(self, test_db):
        import database.db as db
        conn = db.get_connection()
        conn.execute(
            "INSERT INTO sessions (name, game_name, platform, date, start_balance, end_balance, status) "
            "VALUES ('s', 'g', 'desktop', '2026-07-24', 1000, 940, 'reviewed')"
        )
        conn.execute("INSERT INTO uploads (session_id, filename, file_type, file_path) VALUES (1, 'v.mp4', 'video', '/tmp/v.mp4')")
        conn.execute(
            "INSERT INTO video_jobs (session_id, upload_id, status, started_at) "
            "VALUES (1, 1, 'complete', '2026-07-24T10:00:00')"
        )
        conn.commit()
        conn.close()
        jobs = vp.get_video_jobs_for_session(1)
        assert len(jobs) == 1
        assert jobs[0]["status"] == "complete"


# ── _recalc_session_from_events ────────────────────────────────────────────────

class TestRecalcSessionFromEvents:
    def test_noop_when_no_events(self, test_db):
        import database.db as db
        conn = db.get_connection()
        conn.execute(
            "INSERT INTO sessions (name, game_name, platform, date, start_balance, end_balance, status) "
            "VALUES ('s', 'g', 'desktop', '2026-07-24', 1000, 940, 'reviewed')"
        )
        conn.commit()
        conn.close()
        vp._recalc_session_from_events(1)
        conn = db.get_connection()
        s = conn.execute("SELECT spins, rtp FROM sessions WHERE id=1").fetchone()
        conn.close()
        assert s["spins"] is None or s["spins"] == 0

    def test_updates_metrics_from_events(self, test_db):
        import database.db as db
        conn = db.get_connection()
        conn.execute(
            "INSERT INTO sessions (name, game_name, platform, date, start_balance, end_balance, status) "
            "VALUES ('s', 'g', 'desktop', '2026-07-24', 1000, 940, 'reviewed')"
        )
        conn.execute(
            "INSERT INTO events (session_id, event_type, timestamp, bet_amount, win_amount, balance_after) "
            "VALUES (1, 'spin', '2026-07-24T10:00:00', 5, 0, 995)"
        )
        conn.execute(
            "INSERT INTO events (session_id, event_type, timestamp, bet_amount, win_amount, balance_after) "
            "VALUES (1, 'spin', '2026-07-24T10:01:00', 5, 25, 1015)"
        )
        conn.execute(
            "INSERT INTO events (session_id, event_type, timestamp, bet_amount, win_amount, balance_after) "
            "VALUES (1, 'spin', '2026-07-24T10:02:00', 5, 0, 1010)"
        )
        conn.commit()
        conn.close()
        vp._recalc_session_from_events(1)
        conn = db.get_connection()
        s = conn.execute("SELECT spins, total_bets, biggest_win, losing_streak, rtp, end_balance, start_balance, net_result FROM sessions WHERE id=1").fetchone()
        conn.close()
        assert s["spins"] == 3
        assert s["total_bets"] == 15.0
        assert s["biggest_win"] == 25.0
        assert s["losing_streak"] == 1
        assert s["end_balance"] == 1010.0
        assert s["start_balance"] == 1000.0


# ── build_events_from_ocr: timestamp edge cases ────────────────────────────────

class TestBuildEventsFromOcrTimestampEdgeCases:
    def test_timestamp_offset_gt_3600_formats_correctly(self, test_db):
        import database.db as db
        conn = db.get_connection()
        conn.execute(
            "INSERT INTO sessions (name, game_name, platform, date, start_balance, end_balance, status) "
            "VALUES ('s', 'g', 'desktop', '2026-07-24', 1000, 940, 'reviewed')"
        )
        conn.commit()
        session_id = conn.execute("SELECT id FROM sessions").fetchone()["id"]
        conn.close()

        ocr_results = [
            {"fields": {"balance": {"value": 1000.0}, "bet": {"value": 5.0}},
             "overall_confidence": 0.9, "timestamp_seconds": 3661.0,
             "scene_changed": False, "diff_score": 0.0},
        ]
        vp.build_events_from_ocr(ocr_results, session_id=session_id, base_timestamp="2026-07-24T10:00:00")
        conn = db.get_connection()
        row = conn.execute("SELECT timestamp FROM events WHERE session_id=?", (session_id,)).fetchone()
        conn.close()
        assert row is not None
        assert "01:01:01" in row["timestamp"]

    def test_implied_win_without_bet_field(self, test_db):
        import database.db as db
        conn = db.get_connection()
        conn.execute(
            "INSERT INTO sessions (name, game_name, platform, date, start_balance, end_balance, status) "
            "VALUES ('s', 'g', 'desktop', '2026-07-24', 1000, 940, 'reviewed')"
        )
        conn.commit()
        session_id = conn.execute("SELECT id FROM sessions").fetchone()["id"]
        conn.close()

        ocr_results = [
            {"fields": {"balance": {"value": 1000.0}}, "overall_confidence": 0.9,
             "timestamp_seconds": 0.0, "scene_changed": False, "diff_score": 0.0},
        ]
        vp.build_events_from_ocr(ocr_results, session_id=session_id, base_timestamp="2026-07-24T10:00:00")
        conn = db.get_connection()
        row = conn.execute("SELECT bet_amount, win_amount FROM events WHERE session_id=?", (session_id,)).fetchone()
        conn.close()
        assert row["bet_amount"] == 0.0
        assert row["win_amount"] == 0.0


# ── ocr_frames sequential dedup first-frame hash ─────────────────────────────

class TestSequentialOcrDedupFirstFrameHash:
    def test_first_frame_stores_hash_with_dedup_enabled(self, monkeypatch, tmp_path):
        f0 = tmp_path / "f0.jpg"
        arr = np.zeros((8, 8, 3), dtype=np.uint8)
        import cv2
        cv2.imwrite(str(f0), arr)

        frames = [
            {"stored_path": str(f0), "timestamp_seconds": 0.0,
             "scene_changed": False, "diff_score": 0.0},
        ]
        hashes = iter([0b1111])
        monkeypatch.setattr(vp, "_phash", lambda _p: next(hashes))

        def _fake_extract(path, roi_config=None):
            return {"fields": {"balance": {"value": 1000.0}},
                    "overall_confidence": 0.9, "flagged": False}
        monkeypatch.setattr(vp, "extract_fields_from_image", _fake_extract)
        monkeypatch.setattr("engines.ocr_engine.persist_ocr_result", lambda **_k: 1)

        results = vp.ocr_frames(frames, workers=1, dedup_threshold=5)
        assert len(results) == 1
        assert not results[0].get("_deduped")
