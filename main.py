"""Entry point for ReadingRabbit application."""
from __future__ import annotations
import threading
import tkinter as tk
from threading import Event

from src.config import load_config
from src.gui import AppGUI
from src.video_processor import VideoProcessor


def main():
    config = load_config()
    stop_event = Event()

    def start_processing():
        gui.update_status("Processing...")
        processor = VideoProcessor(
            config.video_path,
            config.output_text_path,
            update_callback=lambda frame, prog: (
                gui.show_frame(frame),
                gui.update_progress(prog),
                gui.update_status(f"{prog:.2f}%")
            ),
            stop_event=stop_event,
        )
        processor.process()
        gui.update_status("Completed")

    root = tk.Tk()
    gui = AppGUI(root, on_start=start_processing)
    root.protocol("WM_DELETE_WINDOW", stop_event.set)
    root.mainloop()


if __name__ == "__main__":
    main()
