from __future__ import annotations

from pathlib import Path

from src.config import load_config


def test_load_config_with_preprocessing(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
video_path: sample.mp4
output_text_path: output.txt
resource_summary_path: summary.json
resource_alert_history_path: alerts.csv
analytics_trend_window: 45
ui_layout: COMPACT
ui_scaling: 1.25
log_path: logs/app.log
log_level: debug
ocr_languages:
  - en
  - ja
ocr_preprocessing:
  default:
    resize_scale: 1.4
    use_otsu_threshold: false
  ja:
    apply_to_easyocr: true
    adaptive_threshold_block_size: 21
    adaptive_threshold_c: 1.5
        """,
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.video_path == "sample.mp4"
    assert config.resource_summary_path == "summary.json"
    assert config.resource_alert_history_path == "alerts.csv"
    assert config.analytics_trend_window == 45
    assert config.ui_layout == "compact"
    assert config.ui_scaling == 1.25
    assert config.log_level == "DEBUG"

    preprocessing = config.preprocessing_for(["ja", "en"])
    assert preprocessing["apply_to_easyocr"] is True
    assert preprocessing["adaptive_threshold_block_size"] == 21
    assert "resize_scale" not in preprocessing  # per-language override applied

    default_processing = config.preprocessing_for(["fr"])
    assert default_processing["resize_scale"] == 1.4
    assert default_processing["use_otsu_threshold"] is False
