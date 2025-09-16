from __future__ import annotations

import sys
import threading
import types
from pathlib import Path
from typing import List

import pytest

fake_cv2 = types.SimpleNamespace(
    VideoCapture=lambda *args, **kwargs: None,
    CAP_PROP_FRAME_COUNT=0,
    setNumThreads=lambda value: None,
)

sys.modules.setdefault("cv2", fake_cv2)

from src.config import AppConfig
from src.video_processor import VideoProcessor


class DummyCapture:
    CAP_PROP_FRAME_COUNT = 7

    def __init__(self, frames: List[object]) -> None:
        self._frames = frames
        self._index = 0
        self.opened = True

    def isOpened(self) -> bool:
        return self.opened

    def read(self):
        if self._index >= len(self._frames):
            return False, None
        frame = self._frames[self._index]
        self._index += 1
        return True, frame

    def get(self, prop):
        if prop == DummyCapture.CAP_PROP_FRAME_COUNT:
            return len(self._frames)
        return 0

    def release(self) -> None:
        self.opened = False


def test_video_processor_generates_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    frames = [object() for _ in range(5)]
    capture = DummyCapture(frames)

    class CaptureFactory:
        CAP_PROP_FRAME_COUNT = DummyCapture.CAP_PROP_FRAME_COUNT

        def __call__(self, path: str):
            assert path == "input.mp4"
            return capture

    capture_factory = CaptureFactory()

    def fake_extract_text(frame) -> str:
        return "frame_text"

    def fake_setup_ocr(use_gpu: bool, languages, gpu_index: int, preprocessing) -> None:
        assert languages == ["en"]

    def fake_verify_text(text: str, model: str, use_gpu: bool, prompt: str, gpu_index: int) -> str:
        return text.upper()

    monkeypatch.setattr("src.video_processor.cv2.VideoCapture", capture_factory)
    monkeypatch.setattr("src.video_processor.cv2.CAP_PROP_FRAME_COUNT", DummyCapture.CAP_PROP_FRAME_COUNT)
    monkeypatch.setattr("src.video_processor.cv2.setNumThreads", lambda value: None)
    monkeypatch.setattr("src.video_processor.extract_text", fake_extract_text)
    monkeypatch.setattr("src.video_processor.setup_ocr", fake_setup_ocr)
    monkeypatch.setattr("src.video_processor.verify_text", fake_verify_text)

    output_path = tmp_path / "output.txt"
    config = AppConfig(
        video_path="input.mp4",
        output_text_path=str(output_path),
        use_gpu=False,
        ocr_languages=["en"],
    )

    updates: List[float] = []

    def update_callback(frame, progress: float, eta: float) -> None:
        updates.append(progress)

    processor = VideoProcessor(config=config, update_callback=update_callback, stop_event=threading.Event())
    processor.process()

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8").strip().splitlines()
    assert content == ["FRAME_TEXT" for _ in frames]
    assert updates[-1] == pytest.approx(100.0)
