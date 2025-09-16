"""Configuration handling for ReadingRabbit."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

import yaml


@dataclass
class AppConfig:
    video_path: str
    output_text_path: str
    use_gpu: bool
    gpu_index: int
    ocr_languages: list[str]
    prompt_template: str
    threads: int
    ui_theme: str
    llm_model: str

    monitor_interval: float

    show_resource_usage: bool
    monitor_interval: float
    themes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    resource_history_seconds: int = 90
    resource_chart_height: int = 140



def load_config(path: str | Path = "config.yaml") -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        raise ValueError("Configuration file is empty or invalid.")

    data.setdefault("themes", {})

    monitor_interval = float(data.get("monitor_interval", 1.0) or 1.0)
    if monitor_interval <= 0:
        monitor_interval = 1.0
    data["monitor_interval"] = monitor_interval

    history_seconds = int(float(data.get("resource_history_seconds", 90)) or 90)
    data["resource_history_seconds"] = max(history_seconds, 10)

    chart_height = int(float(data.get("resource_chart_height", 140)) or 140)
    data["resource_chart_height"] = max(chart_height, 80)

    return AppConfig(**data)
