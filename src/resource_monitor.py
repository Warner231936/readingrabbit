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


def get_gpu_usage() -> Tuple[Optional[float], Optional[float]]:
    """Return GPU load and memory usage percentages."""
    if GPUtil is None:
        return None, None
    gpus = GPUtil.getGPUs()
    if not gpus:
        return None, None
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
    ):
        self.update_callback = update_callback
        self.interval = interval
        self.stop_event = stop_event
        self.pause_event = pause_event

    def run(self) -> None:
        while not self.stop_event.is_set():
            if self.pause_event.is_set():
                time.sleep(self.interval)
                continue
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            gpu_load, gpu_mem = get_gpu_usage()
            self.update_callback(cpu, gpu_load, gpu_mem, ram)
            time.sleep(self.interval)
