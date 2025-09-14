"""Video processing logic."""
from __future__ import annotations
import cv2
import time
from pathlib import Path
from threading import Event

from .ocr import extract_text
from .llm import verify_text


class VideoProcessor:
    def __init__(
        self,
        video_path: str,
        output_path: str,
        llm_model: str,
        update_callback,
        stop_event: Event,
    ):
        self.video_path = video_path
        self.output_path = Path(output_path)
        self.llm_model = llm_model
        self.update_callback = update_callback
        self.stop_event = stop_event

    def process(self):
        cap = cv2.VideoCapture(self.video_path)
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
                    text = verify_text(text, self.llm_model)
                    f.write(text + "\n")
                frame_idx += 1
                progress = (frame_idx / total_frames) * 100
                elapsed = time.time() - start_time
                fps = frame_idx / elapsed if elapsed else 0
                eta = (total_frames - frame_idx) / fps if fps else 0
                self.update_callback(frame, progress, eta)
                time.sleep(0.01)  # simulate processing delay
        cap.release()
