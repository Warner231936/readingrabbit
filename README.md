# ReadingRabbit

ReadingRabbit is a Windows-focused application that transcribes in-game chat
from MP4 videos into text. It features a themeable Tkinter GUI, live video
playback, GPU-accelerated OCR, resource monitoring with historical charts, and
LLM-based verification.

## Setup
1. Install Python 3.10+ on Windows 10.
2. (Optional) Install [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) and ensure `tesseract.exe` is on your `PATH` for CPU fallback.
3. Run `install.bat` to create a virtual environment and install dependencies.
4. Configure settings in `config.yaml`.
5. Launch the app with `launch.bat`.

## Configuration
All settings reside in `config.yaml`:
- `video_path`: path to the input MP4 file.
- `output_text_path`: where OCR text will be written.
- `use_gpu`: toggle GPU usage when available.
- `gpu_index`: GPU device index.
- `ocr_languages`: list of language codes for OCR.
- `prompt_template`: template used to craft the LLM prompt.
- `threads`: number of processing threads.
- `ui_theme`: interface theme (currently `dark`).
- `llm_model`: identifier for the LLM used for verification.
- `show_resource_usage`: display CPU/GPU/RAM stats in the GUI.
- `monitor_interval`: seconds between resource updates.
- `resource_history_seconds`: amount of historical resource data to render in the chart.
- `resource_chart_height`: height of the resource history chart in pixels.
- `themes`: collection of named UI themes (e.g., `dark`, `midnight`).

GPU statistics and acceleration require a compatible GPU plus the `gputil`,
`torch`, and `easyocr` packages.

### Theme customization

Select the active theme with `ui_theme`. Each entry in the `themes` section can
override:

- Base colors (`background`, `surface`, `accent`, `text`, `highlight`, `danger`).
- Font family and size (`font`, `font_size`).
- Chart colors for CPU, RAM, GPU, and VRAM lines.

Adjust or add themes to match your preferences. All UI settings remain inside
`config.yaml`, so a single file controls the full experience.

## Usage
1. Place your target MP4 file at the path specified in `config.yaml`.
2. Run `launch.bat` and press **Start** in the GUI.
3. The current video frame, progress percentage, resource usage (including GPU
   load and VRAM), resource history chart, and estimated time remaining will
   appear.
4. Use **Pause Monitor** to stop resource tracking temporarily (the history
   chart pauses as well).
5. OCR output is written to `output_text_path` when processing completes.
6. Close the window or press the standard close button to stop processing.

## Status
This project is under active development. See `AGENTS.md` for detailed
progress tracking and upcoming tasks.

## Troubleshooting
- **Tesseract not found**: Ensure `tesseract.exe` is installed and added to your
  `PATH` if you plan to use CPU fallback.
- **Missing GPU metrics**: Install compatible GPU drivers and verify that the
  `gputil` package detects your hardware.
- **Model download errors**: The first run downloads the `t5-small` model from
  Hugging Face. Confirm internet access or pre-download the model.
- **OCR failures**: Confirm CUDA is available for EasyOCR or fall back to
  Tesseract by setting `use_gpu` to `false`.
- **Placeholder video path**: Update `video_path` in `config.yaml` with an MP4
  file available on your system before starting the app.

## Advanced Usage
- **Selecting a different LLM**: Edit `llm_model` in `config.yaml` with any
  compatible text-to-text model from Hugging Face.
- **Disabling LLM verification**: Set `llm_model` to an empty string to write
  raw OCR text without model correction.
