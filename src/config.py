"""Configuration handling for ReadingRabbit."""
from __future__ import annotations
import yaml
from dataclasses import dataclass
from pathlib import Path


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
    show_resource_usage: bool
    monitor_interval: float


def load_config(path: str | Path = "config.yaml") -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return AppConfig(**data)
