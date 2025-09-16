"""System resource monitoring utilities."""
from __future__ import annotations

import threading
import time
from typing import Callable

import psutil


class ResourceMonitor:
    """Periodically report CPU, RAM, GPU usage and ETA."""

    def __init__(self, callback: Callable[[float, float, float, float], None], interval: float = 1.0, use_gpu: bool = True):
        self.callback = callback
        self.interval = interval
        self.use_gpu = use_gpu
        self._thread: threading.Thread | None = None
        self._running = False
        self._start_time = time.time()
        self.progress = 0.0

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=0)

    def update_progress(self, progress: float) -> None:
        self.progress = progress

    def _run(self) -> None:
        try:
            import GPUtil  # type: ignore
        except Exception:  # pragma: no cover - optional dependency
            GPUtil = None  # type: ignore

        while self._running:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            gpu = 0.0
            if self.use_gpu and GPUtil:
                try:
                    gpus = GPUtil.getGPUs()  # type: ignore
                    if gpus:
                        gpu = gpus[0].load * 100
                except Exception:
                    gpu = 0.0
            elapsed = time.time() - self._start_time
            eta = (elapsed * (100 - self.progress) / self.progress) if self.progress > 0 else 0.0
            self.callback(cpu, ram, gpu, eta)
            time.sleep(self.interval)

