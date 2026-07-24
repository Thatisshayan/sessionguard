"""Focused regression tests for video pipeline frame handling."""

from pathlib import Path

import numpy as np

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


def test_perceptual_hash_helpers_handle_missing_and_distance(tmp_path: Path):
    assert video_pipeline._phash(str(tmp_path / "missing.jpg")) == 0
    assert video_pipeline._hamming_distance(0b1010, 0b0011) == 2
