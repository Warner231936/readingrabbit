"""Configuration handling for ReadingRabbit."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping

import yaml


@dataclass(slots=True)
class AppConfig:
    """Structured configuration for the application."""

    video_path: str
    output_text_path: str
    use_gpu: bool = True
    gpu_index: int = 0
    ocr_languages: list[str] = field(default_factory=lambda: ["en"])
    prompt_template: str = "Correct the OCR text: {text}"
    threads: int = 1
    ui_theme: str = "dark"
    llm_model: str = ""
    show_resource_usage: bool = True
    monitor_interval: float = 1.0
    resource_history_seconds: int = 120
    resource_chart_height: int = 160
    resource_log_path: str | None = None
    resource_alerts: Dict[str, float] = field(default_factory=dict)
    alert_cooldown_seconds: float = 60.0
    themes: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def theme(self) -> Mapping[str, Any] | None:
        """Return the theme mapping for the selected UI theme."""

        return self.themes.get(self.ui_theme)


def _ensure_languages(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return ["en"]


def _ensure_float(value: Any, default: float, minimum: float | None = None) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        result = default
    if minimum is not None:
        result = max(result, minimum)
    return result


def _normalise_alerts(alerts: Any) -> Dict[str, float]:
    if not isinstance(alerts, Mapping):
        return {}
    normalised: Dict[str, float] = {}
    for key, value in alerts.items():
        if value is None:
            continue
        try:
            normalised[str(key).lower()] = float(value)
        except (TypeError, ValueError):
            continue
    return normalised


def load_config(path: str | Path = "config.yaml") -> AppConfig:
    """Load configuration from ``path`` and return an :class:`AppConfig`."""

    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    if not isinstance(data, dict):
        raise ValueError("Configuration file is invalid: expected a mapping at top level.")

    data.setdefault("themes", {})
    data["ocr_languages"] = _ensure_languages(data.get("ocr_languages"))
    data["monitor_interval"] = _ensure_float(data.get("monitor_interval"), 1.0, 0.1)
    data["resource_history_seconds"] = int(
        _ensure_float(data.get("resource_history_seconds"), 120.0, 10)
    )
    data["resource_chart_height"] = int(
        _ensure_float(data.get("resource_chart_height"), 160.0, 80)
    )
    data["alert_cooldown_seconds"] = _ensure_float(
        data.get("alert_cooldown_seconds"), 60.0, 1.0
    )
    data["resource_alerts"] = _normalise_alerts(data.get("resource_alerts"))

    resource_log_path = data.get("resource_log_path")
    data["resource_log_path"] = str(resource_log_path) if resource_log_path else None

    threads = data.get("threads")
    try:
        threads_int = int(threads)
        data["threads"] = max(1, threads_int)
    except (TypeError, ValueError):
        data["threads"] = 1

    return AppConfig(**data)
