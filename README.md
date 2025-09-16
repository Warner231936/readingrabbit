# ReadingRabbit

ReadingRabbit is a Windows-focused application that transcribes in-game chat
from MP4 videos into text. It pairs a themeable Tkinter GUI with live video
playback, GPU-accelerated OCR, optional LLM verification, and detailed resource
monitoring with historical charts, alerts, and CSV exports.

## Features
- GPU-accelerated OCR with EasyOCR and automatic fallback to Tesseract.
- Optional LLM verification for cleaner transcripts using Hugging Face models.
- Dark, cyber-themed Tkinter interface with configurable themes stored in
  `config.yaml`.
- Live video preview, progress updates, and ETA calculations.
- Real-time CPU/GPU/VRAM/RAM monitoring with history charts and pause/resume
  controls.
- Automatic resource alerting with configurable thresholds and cooldowns.
- Resource usage logging to CSV for later analysis.
- Automatic post-run analytics with JSON summaries and optional alert history
  exports.
- Flexible layout presets (stacked or compact) with configurable UI scaling.
- Windows-friendly installer (`install.bat`) and launcher (`launch.bat`).

## Requirements
- Windows 10 with Python 3.10 or later.
- (Optional) CUDA-capable GPU for accelerated OCR and LLM inference.
- (Optional) [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) for
  CPU fallback; ensure `tesseract.exe` is on your `PATH`.

All Python dependencies are listed in `requirements.txt` and installed by the
batch installer.

## Setup
1. Install Python 3.10+ and ensure `python` is on your `PATH`.
2. Clone or extract the ReadingRabbit project folder.
3. Open **Command Prompt** and run `install.bat` from the project directory to
   create a virtual environment and install dependencies.
4. Review and update `config.yaml` (details below) before launching the app.
5. Start the application with `launch.bat`.

## Configuration (`config.yaml`)
All application settings live in `config.yaml`. Key entries:

| Key | Description |
| --- | --- |
| `video_path` | Path to the MP4 file to process. Update from the placeholder `sample.mp4`. |
| `output_text_path` | Where the transcript will be written (directories auto-create). |
| `use_gpu` / `gpu_index` | Enable GPU acceleration and select the GPU device. |
| `ocr_languages` | List of language codes for OCR (e.g., `en`, `de`). |
| `prompt_template` | Template for LLM verification (`{text}` is replaced with OCR output). |
| `threads` | Number of OpenCV worker threads to use. |
| `ui_theme` | Theme name from the `themes` section. |
| `llm_model` | Hugging Face text-to-text model identifier (leave blank to disable verification). |
| `show_resource_usage` | Toggle live monitoring widgets in the GUI. |
| `monitor_interval` | Seconds between resource monitor updates. |
| `resource_history_seconds` | Duration of history to plot in the chart. |
| `resource_chart_height` | Height of the history chart in pixels. |
| `resource_log_path` | CSV file path for resource usage logging. |
| `resource_summary_path` | JSON file path that stores summary analytics after each run. |
| `resource_alert_history_path` | CSV path that captures the alert history when alerts fire. |
| `resource_alerts` | Thresholds (in %) for CPU/RAM/GPU/VRAM alerting. |
| `alert_cooldown_seconds` | Minimum seconds between repeated alerts per metric. |
| `analytics_trend_window` | Seconds of history to analyse for trend reporting in the summary. |
| `ui_layout` | `stacked` (default) or `compact` horizontal layout for the GUI. |
| `ui_scaling` | Tk scaling factor for high-DPI displays (e.g., `1.5`). |
| `log_path` / `log_level` | Location and level for persistent application logs. |
| `themes` | Collection of theme definitions; customize colors, fonts, and chart palettes. |
| `ocr_preprocessing` | Language-aware preprocessing overrides for OCR (resize, filters, thresholds). |

> **Placeholder note:** `video_path` defaults to `sample.mp4`. Replace this value
> with a real video path on your system before running the app.

## Usage
1. Update `config.yaml` with your video path and any desired settings.
2. Run `launch.bat`. The GUI opens with the selected theme.
3. Click **Start** to begin processing. Live progress, ETA, and the current video
   frame appear immediately.
4. Monitor CPU/GPU/VRAM/RAM usage in real time. Click **Pause Monitor** to
   temporarily suspend sampling without stopping the transcription.
5. Resource alerts pop up automatically when usage crosses configured thresholds.
6. When processing finishes, transcripts are written to the `output_text_path`.
7. Review the resource summary banner and (if configured) open the JSON summary
   or alert history directly from the GUI buttons.
8. If resource logging is enabled, click **Open Resource Log** to inspect the CSV
   once it is generated.

## Resource Logging, Analytics, and Alerts
- Resource samples are written to `resource_log_path` (CSV) while monitoring is
  active. Each entry includes UTC timestamps for post-run analysis.
- A JSON summary is generated at `resource_summary_path` after each run with
  averages, minima/maxima, and trend insights for all monitored metrics.
- Alert history is exported to `resource_alert_history_path` whenever thresholds
  are crossed. Open the file straight from the GUI if alerts occurred.
- Alerts respect the per-metric thresholds and cooldown defined in the config.
  Alert messages surface in the GUI, as Windows dialogs, and in the log file.

## Layout and Scaling Presets
- `ui_layout: stacked` recreates the original vertical layout, while
  `ui_layout: compact` arranges monitoring widgets to the right of the video
  preview for widescreen setups.
- Use `ui_scaling` to adjust Tk's DPI scaling for high-resolution displays
  (e.g., `1.25` or `1.5`).

## OCR and Verification Pipeline
- `setup_ocr` initializes EasyOCR with GPU acceleration when available. When
  EasyOCR cannot load, ReadingRabbit falls back to Tesseract with automatic
  preprocessing for clearer text.
- If `llm_model` is defined, OCR output runs through the configured transformer
  pipeline. Clear the field to record raw OCR text without verification.

## Troubleshooting
- **Video fails to open:** Confirm `video_path` points to a valid MP4 file and
  that you have permissions to read it.
- **Missing GPU metrics:** Install the NVIDIA drivers and ensure the `gputil`
  package detects your hardware. If no GPU is available, the monitor shows `N/A`.
- **Tesseract not found:** Install the Windows Tesseract build and add
  `tesseract.exe` to the `PATH`, or install EasyOCR with GPU support.
- **Model download errors:** The first LLM run downloads the chosen model. Ensure
  you have internet access or pre-download the model using `transformers-cli`.
- **Virtual environment issues:** Delete the `venv` folder and rerun
  `install.bat` if dependencies become corrupted.
- **Analytics files missing:** Ensure the directories in `resource_summary_path`
  and `resource_alert_history_path` exist or allow ReadingRabbit to create them.
  Summaries require at least one resource sample; alert logs only appear when
  thresholds are crossed.

## Development Notes
- All runtime options are centralized in `config.yaml` to simplify deployment.
- Logging, alerts, themes, analytics, and monitoring features are designed for
  Windows 10, but the core Python code remains cross-platform for development
  convenience.
- Automated tests cover configuration loading, resource monitoring analytics,
  and the video processor pipeline. Run `pytest` inside the project directory to
  validate changes before shipping.

