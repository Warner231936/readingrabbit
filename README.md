# ReadingRabbit

ReadingRabbit is an evolving Windows-focused application that transcribes
in-game chat from MP4 videos into text. It features a dark, cyber-themed
Tkinter GUI, progress tracking, and plans for GPU-accelerated OCR with LLM
verification. The application now includes live CPU/RAM/GPU monitoring and
an estimated time remaining display during processing.

## Setup
1. Ensure Python 3.10+ is installed on Windows 10.
2. Run `install.bat` to create a virtual environment and install dependencies.
3. Configure settings in `config.yaml`.
4. Launch the app with `launch.bat`.

## Usage
1. Place your input MP4 file at the path specified by `video_path`.
2. Run `launch.bat` and click **Start** in the GUI.
3. During processing, watch live resource usage and ETA. Output text is
   saved to the location defined by `output_text_path`.

## Configuration
All settings reside in `config.yaml`:
- `video_path`: path to the input MP4 file.
- `output_text_path`: where OCR text will be written.
- `use_gpu`: toggle GPU usage when available.
- `threads`: number of processing threads.
- `ui_theme`: interface theme (currently `dark`).
- `llm_model`: identifier for the LLM used for verification.
- `monitor_interval`: seconds between resource usage updates.

## Status
This project is under active development. See `AGENTS.md` for detailed
progress tracking and upcoming tasks.
