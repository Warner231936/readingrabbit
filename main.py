"""Entry point for ReadingRabbit application."""
from __future__ import annotations
import threading
import tkinter as tk
from threading import Event
from typing import Optional

from src.config import load_config
from src.gui import AppGUI
from src.video_processor import VideoProcessor
from src.resource_monitor import ResourceMonitor


def main():
    config = load_config()
    stop_event = Event()
    monitor_pause_event = Event()
    monitor_thread: Optional[threading.Thread] = None

    def toggle_monitor(active: bool) -> None:
        if active:
            monitor_pause_event.clear()
        else:
            monitor_pause_event.set()

    def start_processing():
        gui.update_status("Processing...")
        if config.show_resource_usage:
            monitor = ResourceMonitor(
                update_callback=gui.update_resources,
                interval=config.monitor_interval,
                stop_event=stop_event,
                pause_event=monitor_pause_event,
            )
            nonlocal monitor_thread
            monitor_thread = threading.Thread(target=monitor.run, daemon=True)
            monitor_thread.start()
        processor = VideoProcessor(
            config,
            update_callback=lambda frame, prog, eta: (
                gui.show_frame(frame),
                gui.update_progress(prog),
                gui.update_status(f"{prog:.2f}%"),
                gui.update_eta(eta),
            ),
            stop_event=stop_event,
        )
        try:
            processor.process()
            gui.update_status("Completed")
        except Exception as exc:
            gui.show_error(str(exc))
            gui.update_status("Error")

    root = tk.Tk()
    gui = AppGUI(
        root,
        on_start=start_processing,
        on_toggle_monitor=toggle_monitor if config.show_resource_usage else None,
    )
    root.protocol("WM_DELETE_WINDOW", stop_event.set)
    root.mainloop()


if __name__ == "__main__":
    main()
