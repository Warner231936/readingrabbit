from __future__ import annotations

import threading
from pathlib import Path
from types import SimpleNamespace
from typing import List

import pytest

from src import resource_monitor
from src.resource_monitor import ResourceMonitor


def test_resource_monitor_writes_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cpu_sequence = [10.0, 25.0, 60.0, 45.0, 30.0]
    call_index = {"count": 0}

    def fake_cpu_percent(interval=None):  # type: ignore[override]
        value = cpu_sequence[min(call_index["count"], len(cpu_sequence) - 1)]
        call_index["count"] += 1
        return value

    def fake_virtual_memory():  # type: ignore[override]
        return SimpleNamespace(percent=40.0)

    monkeypatch.setattr(resource_monitor.psutil, "cpu_percent", fake_cpu_percent)
    monkeypatch.setattr(resource_monitor.psutil, "virtual_memory", fake_virtual_memory)
    monkeypatch.setattr(resource_monitor, "get_gpu_usage", lambda gpu_index: (50.0, 55.0))

    stop_event = threading.Event()
    pause_event = threading.Event()
    metrics: List[float] = []
    alerts: List[str] = []

    def update_callback(cpu, gpu, vram, ram):
        metrics.append(cpu)
        if len(metrics) >= 4:
            stop_event.set()

    def alert_callback(metric: str, value: float) -> None:
        alerts.append(metric)

    summary_path = tmp_path / "summary.json"
    alert_path = tmp_path / "alerts.csv"

    monitor = ResourceMonitor(
        update_callback=update_callback,
        interval=0.01,
        stop_event=stop_event,
        pause_event=pause_event,
        gpu_index=None,
        log_path=tmp_path / "samples.csv",
        alert_thresholds={"cpu": 20},
        alert_callback=alert_callback,
        alert_cooldown=0.0,
        summary_path=str(summary_path),
        alert_log_path=str(alert_path),
        trend_window=0.05,
    )

    thread = threading.Thread(target=monitor.run, daemon=True)
    thread.start()
    thread.join(timeout=2)

    assert not thread.is_alive(), "Monitor thread should terminate"
    assert monitor.summary_text is not None
    assert "Alerts triggered" in monitor.summary_text
    assert summary_path.exists()
    assert alert_path.exists()
    assert alerts, "Alert callback should have fired"
