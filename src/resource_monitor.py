"""Resource monitoring utilities for ReadingRabbit."""
from __future__ import annotations
import time
from threading import Event
from typing import Callable, Optional

import psutil

try:
    import GPUtil
except Exception:  # GPUtil is optional
    GPUtil = None


def get_gpu_usage() -> Optional[float]:
    """Return GPU load percentage if available, otherwise ``None``."""
    if GPUtil is None:
        return None
    gpus = GPUtil.getGPUs()
    if not gpus:
        return None
    return gpus[0].load * 100


class ResourceMonitor:
    """Monitors system resources and reports via callback."""

    def __init__(self, update_callback: Callable[[float, Optional[float], float], None], interval: float, stop_event: Event):
        self.update_callback = update_callback
        self.interval = interval
        self.stop_event = stop_event

    def run(self):
        while not self.stop_event.is_set():
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            gpu = get_gpu_usage()
            self.update_callback(cpu, gpu, ram)
            time.sleep(self.interval)
