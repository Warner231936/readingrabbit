
"""Resource monitoring utilities for ReadingRabbit."""
from __future__ import annotations

import csv
import json
import logging
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from typing import Callable, Dict, List, Optional, Tuple

import psutil

try:
    import GPUtil  # type: ignore
except Exception:  # GPUtil is optional at runtime
    GPUtil = None  # type: ignore


UpdateCallback = Callable[[float, Optional[float], Optional[float], float], None]
AlertCallback = Callable[[str, float], None]


def get_gpu_usage(gpu_index: Optional[int] = None) -> Tuple[Optional[float], Optional[float]]:
    """Return GPU load and memory usage percentages."""

    if GPUtil is None:
        return None, None
    try:
        gpus = GPUtil.getGPUs()  # type: ignore[attr-defined]
    except Exception:
        return None, None
    if not gpus:
        return None, None
    index = gpu_index if gpu_index is not None else 0
    try:
        gpu = gpus[index]
    except IndexError:
        gpu = gpus[0]
    return gpu.load * 100, gpu.memoryUtil * 100


class ResourceMonitor:
    """Monitors system resources and reports via callback."""

    def __init__(
        self,
        update_callback: UpdateCallback,
        interval: float,
        stop_event: Event,
        pause_event: Event,
        *,
        gpu_index: Optional[int] = None,
        log_path: Optional[str] = None,
        alert_thresholds: Optional[Dict[str, float]] = None,
        alert_callback: Optional[AlertCallback] = None,
        alert_cooldown: float = 60.0,
        summary_path: Optional[str] = None,
        alert_log_path: Optional[str] = None,
        trend_window: float = 60.0,
    ) -> None:
        self.update_callback = update_callback
        self.interval = max(0.1, float(interval))
        self.stop_event = stop_event
        self.pause_event = pause_event
        self.gpu_index = gpu_index
        self.log_path = Path(log_path).expanduser() if log_path else None
        self.alert_thresholds = {
            key.lower(): float(value)
            for key, value in (alert_thresholds or {}).items()
            if value is not None
        }
        self.alert_callback = alert_callback
        self.alert_cooldown = max(0.0, float(alert_cooldown))
        self._last_alerts: Dict[str, float] = {}
        self.summary_path = Path(summary_path).expanduser() if summary_path else None
        self.alert_log_path = Path(alert_log_path).expanduser() if alert_log_path else None
        self.trend_window = max(10.0, float(trend_window))
        self.samples: List[Dict[str, float]] = []
        self.sample_times: List[float] = []
        self.summary_data: Optional[Dict[str, Dict[str, float]]] = None
        self.summary_text: Optional[str] = None
        self.alert_history: List[Tuple[str, str, float]] = []
        self._logger = logging.getLogger("readingrabbit")

    def run(self) -> None:
        csv_file = None
        writer = None
        if self.log_path is not None:
            try:
                self.log_path.parent.mkdir(parents=True, exist_ok=True)
                csv_file = self.log_path.open("w", newline="", encoding="utf-8")
                writer = csv.writer(csv_file)
                writer.writerow(["timestamp", "cpu", "ram", "gpu", "vram"])
            except Exception:
                csv_file = None
                writer = None

        # Prime CPU stats to avoid the first call returning 0.0
        psutil.cpu_percent(interval=None)

        try:
            while not self.stop_event.is_set():
                if self.pause_event.is_set():
                    time.sleep(self.interval)
                    continue

                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                gpu_load, gpu_mem = get_gpu_usage(self.gpu_index)

                self.samples.append(
                    {
                        "cpu": float(cpu),
                        "ram": float(ram),
                        "gpu": float(gpu_load) if gpu_load is not None else float("nan"),
                        "vram": float(gpu_mem) if gpu_mem is not None else float("nan"),
                    }
                )
                self.sample_times.append(time.monotonic())

                if writer is not None and csv_file is not None:
                    timestamp = datetime.now(timezone.utc).isoformat()
                    writer.writerow(
                        [
                            timestamp,
                            f"{cpu:.2f}",
                            f"{ram:.2f}",
                            "" if gpu_load is None else f"{gpu_load:.2f}",
                            "" if gpu_mem is None else f"{gpu_mem:.2f}",
                        ]
                    )
                    csv_file.flush()

                self.update_callback(cpu, gpu_load, gpu_mem, ram)
                self._check_alerts(cpu, gpu_load, gpu_mem, ram)

                time.sleep(self.interval)
        finally:
            if csv_file is not None:
                csv_file.close()
            self._finalise_summary()

    def _finalise_summary(self) -> None:
        if not self.samples:
            return

        summary: Dict[str, Dict[str, float]] = {}
        trend_summary: Dict[str, float] = {}
        window_seconds = self.trend_window
        if self.sample_times:
            cutoff = self.sample_times[-1] - window_seconds
        else:
            cutoff = 0.0

        metrics = ("cpu", "ram", "gpu", "vram")
        for metric in metrics:
            values = [sample[metric] for sample in self.samples if not _is_nan(sample[metric])]
            if not values:
                continue
            summary[metric] = {
                "average": statistics.fmean(values),
                "maximum": max(values),
                "minimum": min(values),
            }

        for metric in metrics:
            window_values = [
                sample[metric]
                for sample, timestamp in zip(self.samples, self.sample_times)
                if timestamp >= cutoff and not _is_nan(sample[metric])
            ]
            if not window_values:
                continue
            trend_summary[metric] = window_values[-1] - window_values[0]

        self.summary_data = summary
        lines = ["Resource Summary:"]
        for metric, stats in summary.items():
            trend = trend_summary.get(metric)
            trend_text = ""
            if trend is not None:
                direction = "increased" if trend > 0 else "decreased" if trend < 0 else "stayed level"
                trend_text = f" (trend {direction} by {abs(trend):.1f}%)"
            lines.append(
                "- {name}: avg {avg:.1f}% | max {mx:.1f}% | min {mn:.1f}%{trend}".format(
                    name=metric.upper(),
                    avg=stats["average"],
                    mx=stats["maximum"],
                    mn=stats["minimum"],
                    trend=trend_text,
                )
            )

        if self.alert_history:
            lines.append(f"- Alerts triggered: {len(self.alert_history)} (see alert log)")
        else:
            lines.append("- Alerts triggered: none")

        self.summary_text = "\n".join(lines)

        if self.summary_path is not None:
            try:
                self.summary_path.parent.mkdir(parents=True, exist_ok=True)
                with self.summary_path.open("w", encoding="utf-8") as handle:
                    json.dump(
                        {
                            "generated": datetime.now(timezone.utc).isoformat(),
                            "interval": self.interval,
                            "trend_window": window_seconds,
                            "metrics": summary,
                            "trend": trend_summary,
                            "alerts_triggered": len(self.alert_history),
                        },
                        handle,
                        indent=2,
                    )
            except Exception as exc:  # pragma: no cover - best effort
                self._logger.error("Failed to write resource summary: %s", exc)

        if self.alert_log_path is not None and self.alert_history:
            try:
                self.alert_log_path.parent.mkdir(parents=True, exist_ok=True)
                with self.alert_log_path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(["timestamp", "metric", "value"])
                    writer.writerows(self.alert_history)
            except Exception as exc:  # pragma: no cover - best effort
                self._logger.error("Failed to write alert history: %s", exc)

    def _check_alerts(
        self,
        cpu: float,
        gpu: Optional[float],
        vram: Optional[float],
        ram: float,
    ) -> None:
        if not self.alert_thresholds or not self.alert_callback:
            return

        metrics = {
            "cpu": cpu,
            "ram": ram,
            "gpu": gpu,
            "vram": vram,
        }
        now = time.monotonic()
        for key, threshold in self.alert_thresholds.items():
            value = metrics.get(key)
            if value is None:
                continue
            if value >= threshold:
                last = self._last_alerts.get(key)
                if last is not None and (now - last) < self.alert_cooldown:
                    continue
                self._last_alerts[key] = now
                timestamp = datetime.now(timezone.utc).isoformat()
                self.alert_history.append((timestamp, key.upper(), float(value)))
                try:
                    self.alert_callback(key, value)
                except Exception:
                    # Alerts should never break monitoring
                    pass


def _is_nan(value: float) -> bool:
    return value != value

