
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


"""Resource monitoring utilities for ReadingRabbit."""
from __future__ import annotations

import time
from threading import Event
from typing import Callable, Optional, Tuple

import psutil

try:
    import GPUtil
except Exception:  # GPUtil is optional
    GPUtil = None


def get_gpu_usage(gpu_index: Optional[int] = None) -> Tuple[Optional[float], Optional[float]]:
    """Return GPU load and memory usage percentages.

    Parameters
    ----------
    gpu_index:
        Preferred GPU index to sample. If ``None`` the first available GPU is
        used.
    """
    if GPUtil is None:
        return None, None
    try:
        gpus = GPUtil.getGPUs()
    except Exception:
        return None, None
    if not gpus:
        return None, None
    index = gpu_index or 0
    try:
        gpu = gpus[index]
    except IndexError:
        gpu = gpus[0]
    return gpu.load * 100, gpu.memoryUtil * 100


class ResourceMonitor:
    """Monitors system resources and reports via callback."""

    def __init__(
        self,
        update_callback: Callable[[float, Optional[float], Optional[float], float], None],
        interval: float,
        stop_event: Event,
        pause_event: Event,
        gpu_index: Optional[int] = None,
    ):
        self.update_callback = update_callback
        self.interval = interval
        self.stop_event = stop_event
        self.pause_event = pause_event
        self.gpu_index = gpu_index

    def run(self) -> None:
        while not self.stop_event.is_set():
            if self.pause_event.is_set():
                time.sleep(self.interval)
                continue
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            gpu_load, gpu_mem = get_gpu_usage(self.gpu_index)
            self.update_callback(cpu, gpu_load, gpu_mem, ram)
            time.sleep(self.interval)

