"""Configuration handling for ReadingRabbit."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

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
    resource_summary_path: str | None = None
    resource_alert_history_path: str | None = None
    resource_alerts: Dict[str, float] = field(default_factory=dict)
    alert_cooldown_seconds: float = 60.0
    analytics_trend_window: float = 60.0
    ui_layout: str = "stacked"
    ui_scaling: float = 1.0
    log_path: str | None = None
    log_level: str = "INFO"
    themes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    ocr_preprocessing: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def theme(self) -> Mapping[str, Any] | None:
        """Return the theme mapping for the selected UI theme."""

        return self.themes.get(self.ui_theme)

    def preprocessing_for(self, languages: Sequence[str]) -> Mapping[str, Any]:
        """Return preprocessing options for the preferred language."""

        if not self.ocr_preprocessing:
            return {}
        for lang in languages:
            lang_key = str(lang).lower()
            if lang_key in self.ocr_preprocessing:
                return self.ocr_preprocessing[lang_key]
        return self.ocr_preprocessing.get("default", {})


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


def _ensure_path_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _normalise_preprocessing(config: Any) -> Dict[str, Dict[str, Any]]:
    if not isinstance(config, Mapping):
        return {}

    normalised: Dict[str, Dict[str, Any]] = {}
    for key, value in config.items():
        if not isinstance(value, Mapping):
            continue
        options: Dict[str, Any] = {}
        for opt_key, opt_value in value.items():
            key_lower = str(opt_key).lower()
            if key_lower in {
                "grayscale",
                "apply_to_easyocr",
                "use_adaptive_threshold",
                "use_otsu_threshold",
            }:
                options[key_lower] = bool(opt_value)
            elif key_lower in {
                "bilateral_diameter",
                "bilateral_sigma_color",
                "bilateral_sigma_space",
                "adaptive_threshold_block_size",
                "clahe_tile_grid_size",
            }:
                try:
                    options[key_lower] = int(opt_value)
                except (TypeError, ValueError):
                    continue
            elif key_lower in {
                "clahe_clip_limit",
                "adaptive_threshold_c",
                "resize_scale",
                "sharpen_amount",
            }:
                try:
                    options[key_lower] = float(opt_value)
                except (TypeError, ValueError):
                    continue
        if options:
            normalised[str(key).lower()] = options
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
    data["resource_log_path"] = _ensure_path_str(data.get("resource_log_path"))
    data["resource_summary_path"] = _ensure_path_str(data.get("resource_summary_path"))
    data["resource_alert_history_path"] = _ensure_path_str(
        data.get("resource_alert_history_path")
    )
    data["log_path"] = _ensure_path_str(data.get("log_path"))
    data["log_level"] = str(data.get("log_level", "INFO")).upper()
    data["analytics_trend_window"] = _ensure_float(
        data.get("analytics_trend_window"),
        60.0,
        10.0,
    )
    data["ui_layout"] = str(data.get("ui_layout", "stacked")).lower()
    data["ui_scaling"] = _ensure_float(data.get("ui_scaling"), 1.0, 0.5)
    data["ocr_preprocessing"] = _normalise_preprocessing(data.get("ocr_preprocessing"))

    threads = data.get("threads")
    try:
        threads_int = int(threads)
        data["threads"] = max(1, threads_int)
    except (TypeError, ValueError):
        data["threads"] = 1

    return AppConfig(**data)
