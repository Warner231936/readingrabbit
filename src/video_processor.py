"""Video processing logic."""
from __future__ import annotations

import time
from pathlib import Path
from threading import Event
from typing import Callable, Optional

import cv2

from .config import AppConfig
from .llm import verify_text
from .logger import get_logger
from .ocr import extract_text, setup_ocr


FrameType = object  # numpy.ndarray, but keep loose typing to avoid runtime dependency
UpdateCallback = Callable[[Optional[FrameType], float, float], None]


class VideoProcessor:
    def __init__(self, config: AppConfig, update_callback: UpdateCallback, stop_event: Event):
        self.config = config
        self.output_path = Path(config.output_text_path)
        self.update_callback = update_callback
        self.stop_event = stop_event
        self.logger = get_logger()

    def process(self) -> None:
        self.logger.info("Initialising video processor for: %s", self.config.video_path)
        setup_ocr(
            self.config.use_gpu,
            self.config.ocr_languages,
            self.config.gpu_index,
            self.config.preprocessing_for(self.config.ocr_languages),
        )
        if self.config.threads:
            try:
                cv2.setNumThreads(int(self.config.threads))
            except Exception:
                pass

        cap = cv2.VideoCapture(self.config.video_path)
        if not cap.isOpened():
            raise FileNotFoundError(f"Cannot open video: {self.config.video_path}")

        total_frames = max(int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1, 1)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        start_time = time.time()
        frame_idx = 0
        cancelled = False

        with self.output_path.open("w", encoding="utf-8") as handle:
            while not self.stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    break

                frame_idx += 1
                try:
                    text = extract_text(frame)
                except Exception as exc:
                    self.logger.error("OCR failure on frame %s: %s", frame_idx, exc)
                    text = ""
                if text:
                    cleaned = verify_text(
                        text,
                        self.config.llm_model,
                        self.config.use_gpu,
                        self.config.prompt_template,
                        self.config.gpu_index,
                    )
                    handle.write(cleaned + "\n")
                    handle.flush()

                progress = min(100.0, (frame_idx / total_frames) * 100)
                elapsed = time.time() - start_time
                fps = frame_idx / elapsed if elapsed > 0 else 0.0
                eta = max(0.0, (total_frames - frame_idx) / fps) if fps > 0 else 0.0

                self.update_callback(frame, progress, eta)

                if self.stop_event.is_set():
                    cancelled = True
                    break

            else:
                cancelled = True

        cap.release()

        if not cancelled and not self.stop_event.is_set():
            # Ensure the final 100% update is issued for short clips.
            self.update_callback(None, 100.0, 0.0)
            self.logger.info("Video processing completed: %s", self.output_path)
        elif cancelled:
            self.logger.info("Video processing cancelled")
