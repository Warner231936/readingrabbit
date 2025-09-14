# ReadingRabbit

ReadingRabbit is an evolving Windows-focused application that transcribes
in-game chat from MP4 videos into text. It features a dark, cyber-themed
Tkinter GUI, progress tracking, and plans for GPU-accelerated OCR with LLM
verification.

## Setup
1. Install Python 3.10+ on Windows 10.
2. Install [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) and ensure `tesseract.exe` is on your `PATH`.
3. Run `install.bat` to create a virtual environment and install dependencies.
4. Configure settings in `config.yaml`.
5. Launch the app with `launch.bat`.

## Configuration
All settings reside in `config.yaml`:
- `video_path`: path to the input MP4 file.
- `output_text_path`: where OCR text will be written.
- `use_gpu`: toggle GPU usage when available.
- `threads`: number of processing threads.
- `ui_theme`: interface theme (currently `dark`).
- `llm_model`: identifier for the LLM used for verification.
- `show_resource_usage`: display CPU/GPU/RAM stats in the GUI.
- `monitor_interval`: seconds between resource updates.

GPU statistics require a compatible GPU and the `gputil` package.

## Usage
1. Place your target MP4 file at the path specified in `config.yaml`.
2. Run `launch.bat` and press **Start** in the GUI.
3. The current video frame, progress percentage, resource usage, and estimated
   time remaining will appear.
4. OCR output is written to `output_text_path` when processing completes.
5. Close the window or press the standard close button to stop processing.

## Status
This project is under active development. See `AGENTS.md` for detailed
progress tracking and upcoming tasks.

## Troubleshooting
- **Tesseract not found**: Ensure `tesseract.exe` is installed and added to
  your `PATH`.
- **Missing GPU metrics**: Install compatible GPU drivers and verify that the
  `gputil` package detects your hardware.
- **Model download errors**: The first run downloads the `t5-small` model from
  Hugging Face. Confirm internet access or pre-download the model.

## Advanced Usage
- **Selecting a different LLM**: Edit `llm_model` in `config.yaml` with any
  compatible text-to-text model from Hugging Face.
- **Disabling LLM verification**: Set `llm_model` to an empty string to write
  raw OCR text without model correction.
