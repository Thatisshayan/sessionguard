"""Focused regression tests for video pipeline frame handling."""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

import engines.video_pipeline as video_pipeline


def test_extract_frames_rejects_missing_video(tmp_path: Path):
    result = video_pipeline.extract_frames(str(tmp_path / "missing.mp4"))

    assert result["success"] is False
    assert "Video not found" in result["error"]
    assert result["frames"] == []


def test_extract_frames_records_scene_changes(monkeypatch, tmp_path: Path):
    video_path = tmp_path / "sample.mp4"
    video_path.touch()

    class FakeCapture:
        def __init__(self, _path):
            self.frames = [
                np.zeros((4, 4, 3), dtype=np.uint8),
                np.zeros((4, 4, 3), dtype=np.uint8),
                np.full((4, 4, 3), 255, dtype=np.uint8),
            ]

        def isOpened(self):
            return True

        def get(self, _property):
            return 2.0

        def read(self):
            if self.frames:
                return True, self.frames.pop(0)
            return False, None

        def release(self):
            pass

    monkeypatch.setattr(video_pipeline.cv2, "VideoCapture", FakeCapture)
    monkeypatch.setattr(video_pipeline.cv2, "imwrite", lambda *_args: True)

    result = video_pipeline.extract_frames(
        str(video_path), fps=1.0, output_dir=str(tmp_path / "frames"), scene_threshold=1.0
    )

    assert result["success"] is True
    assert result["frame_count"] == 2
    assert result["scene_change_count"] == 1
    assert result["frames"][1]["scene_changed"] is True
    assert result["frames"][1]["timestamp_seconds"] == 1.0


def test_extract_frames_unopenable_video_returns_failure(monkeypatch, tmp_path: Path):
    video_path = tmp_path / "broken.mp4"
    video_path.touch()

    class _ClosedCapture:
        def isOpened(self):
            return False
        def get(self, _p):
            return 25.0
        def read(self):
            return False, None
        def release(self):
            pass

    monkeypatch.setattr(video_pipeline.cv2, "VideoCapture", lambda *_a, **_k: _ClosedCapture())

    result = video_pipeline.extract_frames(str(video_path), output_dir=str(tmp_path / "frames"))
    assert result["success"] is False
    assert result["error"] == "Could not open video with OpenCV."


def test_perceptual_hash_helpers_handle_missing_and_distance(tmp_path: Path):
    assert video_pipeline._phash(str(tmp_path / "missing.jpg")) == 0
    assert video_pipeline._hamming_distance(0b1010, 0b0011) == 2


class TestCheckFfmpeg:
    def test_returns_available_when_on_path(self, monkeypatch):
        monkeypatch.setattr(video_pipeline.shutil, "which", lambda _n: "/usr/bin/ffmpeg")

        class _Result:
            stdout = "ffmpeg version 6.0\n"

        monkeypatch.setattr(video_pipeline.subprocess, "run", lambda *_a, **_k: _Result())
        r = video_pipeline.check_ffmpeg()
        assert r["available"] is True
        assert r["path"] == "/usr/bin/ffmpeg"
        assert "6.0" in r["version"]

    def test_returns_unavailable_when_absent(self, monkeypatch):
        monkeypatch.setattr(video_pipeline.shutil, "which", lambda _n: None)
        r = video_pipeline.check_ffmpeg()
        assert r["available"] is False
        assert r["path"] is None
        assert "not found" in r["message"].lower()

    def test_returns_unavailable_on_run_error(self, monkeypatch):
        monkeypatch.setattr(video_pipeline.shutil, "which", lambda _n: "/usr/bin/ffmpeg")
        def _boom(*_a, **_k):
            raise RuntimeError("permission denied")
        monkeypatch.setattr(video_pipeline.subprocess, "run", _boom)
        r = video_pipeline.check_ffmpeg()
        assert r["available"] is False
        assert r["path"] == "/usr/bin/ffmpeg"
        assert "permission denied" in r["message"]


@pytest.fixture
def _chunk_schema(monkeypatch, test_db):
    """V11 (chunk columns) isn't applied by conftest; add it for chunk tests."""
    from database.db import init_db_v11
    init_db_v11()
    # Seed a session + upload so the video_jobs FK is satisfied.
    import database.db as db
    conn = db.get_connection()
    conn.execute(
        "INSERT INTO sessions (name, game_name, platform, date, start_balance, end_balance) "
        "VALUES ('s', 'g', 'desktop', '2026-07-24', 1000, 940)"
    )
    conn.execute("INSERT INTO uploads (session_id, filename, file_type, file_path) VALUES (1, 'v.mp4', 'video', '/tmp/v.mp4')")
    conn.commit()
    conn.close()
    return test_db


def _seed_minimal_session():
    """Insert a session with only the NOT-NULL columns required by the events FK."""
    import database.db as db
    conn = db.get_connection()
    conn.execute(
        "INSERT INTO sessions (name, game_name, platform, date, start_balance, end_balance, status) "
        "VALUES ('s', 'g', 'desktop', '2026-07-24', 1000, 940, 'reviewed')"
    )
    conn.commit()
    session_id = conn.execute("SELECT id FROM sessions").fetchone()["id"]
    conn.close()
    return session_id


class TestVideoJobChunkHelpers:
    def test_progress_chunks_default_to_zero_when_absent(self, _chunk_schema):
        # No matching job row: helper must not raise; returns (0, 0).
        assert video_pipeline._get_job_progress_chunks(999999) == (0, 0)

    def test_checkpoint_and_read_roundtrip(self, _chunk_schema):
        import database.db as db
        conn = db.get_connection()
        conn.execute(
            "INSERT INTO video_jobs (session_id, upload_id, status, current_chunk, total_chunks) "
            "VALUES (1, 1, 'running', 0, 4)"
        )
        conn.commit()
        job_id = conn.execute("SELECT id FROM video_jobs").fetchone()["id"]
        conn.close()

        assert video_pipeline._get_job_progress_chunks(job_id) == (0, 4)
        video_pipeline._checkpoint_job_chunk(job_id, 2)
        assert video_pipeline._get_job_progress_chunks(job_id) == (2, 4)


class TestBuildEventsFromOcr:
    def test_returns_zero_when_no_balance_fields(self, test_db):
        # No balance value -> no events created; review items stay zero.
        ocr_results = [
            {"fields": {"bet": {"value": 5.0}, "win": {"value": 0.0}},
             "overall_confidence": 0.9, "timestamp_seconds": 0.0},
            {"fields": {}, "overall_confidence": 0.9, "timestamp_seconds": 1.0},
        ]
        events, review = video_pipeline.build_events_from_ocr(
            ocr_results, session_id=1, base_timestamp="2026-07-24T10:00:00"
        )
        assert (events, review) == (0, 0)

    def test_creates_event_and_flags_low_confidence(self, test_db):
        session_id = _seed_minimal_session()

        ocr_results = [
            # balance present but below the 0.75 confidence threshold -> review
            {"fields": {"balance": {"value": 1000.0}, "bet": {"value": 5.0},
                        "win": {"value": 0.0}},
             "overall_confidence": 0.4, "timestamp_seconds": 0.0,
             "scene_changed": False, "diff_score": 0.0},
            # high confidence -> event, no review
            {"fields": {"balance": {"value": 1015.0}, "bet": {"value": 5.0},
                        "win": {"value": 25.0}},
             "overall_confidence": 0.9, "timestamp_seconds": 1.0,
             "scene_changed": False, "diff_score": 0.0},
        ]
        events, review = video_pipeline.build_events_from_ocr(
            ocr_results, session_id=session_id, base_timestamp="2026-07-24T10:00:00"
        )
        assert events == 2
        assert review == 1  # only the low-confidence one

        import database.db as db
        conn = db.get_connection()
        event_rows = conn.execute(
            "SELECT bet_amount, win_amount, balance_after, confidence_score, source "
            "FROM events WHERE session_id=? ORDER BY id", (session_id,)
        ).fetchall()
        rev_rows = conn.execute(
            "SELECT reason FROM review_items WHERE session_id=?", (session_id,)
        ).fetchall()
        conn.close()
        assert len(event_rows) == 2
        assert event_rows[0]["source"] == "ocr"
        assert event_rows[1]["balance_after"] == 1015.0
        assert len(rev_rows) == 1
        assert "0.40" in rev_rows[0]["reason"]

    def test_derives_implied_win_from_balance_delta(self, test_db):
        session_id = _seed_minimal_session()

        # No win field but balance rises from 1000 -> 1015 with bet 5 -> implied 20.
        ocr_results = [
            {"fields": {"balance": {"value": 1000.0}, "bet": {"value": 5.0}},
             "overall_confidence": 0.9, "timestamp_seconds": 0.0},
            {"fields": {"balance": {"value": 1015.0}, "bet": {"value": 5.0}},
             "overall_confidence": 0.9, "timestamp_seconds": 1.0},
        ]
        events, _ = video_pipeline.build_events_from_ocr(
            ocr_results, session_id=session_id, base_timestamp="2026-07-24T10:00:00"
        )
        assert events == 2
        import database.db as db
        conn = db.get_connection()
        rows = conn.execute(
            "SELECT win_amount FROM events WHERE session_id=? ORDER BY id", (session_id,)
        ).fetchall()
        conn.close()
        # First event has no prior balance -> win defaults to 0 (bet-None path skipped);
        # second derives 1015 - 1000 + 5 = 20.
        assert rows[1]["win_amount"] == 20.0


class TestSequentialOcrDedup:
    def test_dedup_skips_near_identical_frames(self, monkeypatch, tmp_path):
        """When dedup_threshold > 0, a frame whose pHash matches the last
        within threshold reuses the previous OCR result instead of re-running."""
        # Three frames; the second has a near-identical hash to the first.
        frames = [
            {"stored_path": str(tmp_path / "f0.jpg"), "timestamp_seconds": 0.0,
             "scene_changed": False, "diff_score": 0.0},
            {"stored_path": str(tmp_path / "f1.jpg"), "timestamp_seconds": 1.0,
             "scene_changed": False, "diff_score": 0.0},
            {"stored_path": str(tmp_path / "f2.jpg"), "timestamp_seconds": 2.0,
             "scene_changed": True, "diff_score": 30.0},
        ]
        hashes = [0b1111, 0b1111, 0b0000]  # f1 == f0 within threshold; f2 differs.
        hash_iter = iter(hashes)
        ocr_calls = []
        def _fake_extract(path, roi_config=None):
            ocr_calls.append(path)
            return {"fields": {"balance": {"value": float(len(ocr_calls) * 1000)}},
                    "overall_confidence": 0.9, "flagged": False}
        # Avoid persisting to a real DB by stubbing persist_ocr_result.
        monkeypatch.setattr(video_pipeline, "_phash", lambda _p: next(hash_iter))
        monkeypatch.setattr(video_pipeline, "extract_fields_from_image", _fake_extract)
        import engines.ocr_engine as ocr_engine
        monkeypatch.setattr(ocr_engine, "persist_ocr_result", lambda **_k: 1)
        monkeypatch.setattr(video_pipeline, "persist_ocr_result", lambda **_k: 1)

        results = video_pipeline.ocr_frames(frames, workers=1, dedup_threshold=2)
        # Only frames 0 and 2 hit the OCR engine; f1 reuses f0's result.
        assert ocr_calls == [str(tmp_path / "f0.jpg"), str(tmp_path / "f2.jpg")]
        assert results[1].get("_deduped") is True
        assert results[1]["fields"]["balance"]["value"] == 1000.0  # reused from f0
