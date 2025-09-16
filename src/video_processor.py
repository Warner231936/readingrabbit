"""Video processing logic."""
from __future__ import annotations
import cv2
import time
from pathlib import Path
from threading import Event
from typing import Callable

from .config import AppConfig
from .ocr import extract_text, setup_ocr
from .llm import verify_text


class VideoProcessor:
    def __init__(self, config: AppConfig, update_callback: Callable, stop_event: Event):
        self.config = config
        self.output_path = Path(config.output_text_path)
        self.update_callback = update_callback
        self.stop_event = stop_event

    def process(self) -> None:
        setup_ocr(self.config.use_gpu, self.config.ocr_languages, self.config.gpu_index)
        cap = cv2.VideoCapture(self.config.video_path)
        if not cap.isOpened():
            raise FileNotFoundError(f"Cannot open video: {self.config.video_path}")
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        start_time = time.time()
        with self.output_path.open("w", encoding="utf-8") as f:
            frame_idx = 0
            while not self.stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    break
                text = extract_text(frame)
                if text:
                    text = verify_text(
                        text,
                        self.config.llm_model,
                        self.config.use_gpu,
                        self.config.prompt_template,
                        self.config.gpu_index,
                    )
                    f.write(text + "\n")
                frame_idx += 1
                progress = (frame_idx / total_frames) * 100
                elapsed = time.time() - start_time
                fps = frame_idx / elapsed if elapsed else 0
                eta = (total_frames - frame_idx) / fps if fps else 0
                self.update_callback(frame, progress, eta)
                time.sleep(0.01)  # simulate processing delay
        cap.release()
