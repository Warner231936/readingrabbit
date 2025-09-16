"""Entry point for ReadingRabbit application."""
from __future__ import annotations
import threading
import tkinter as tk
from threading import Event

from src.config import load_config
from src.gui import AppGUI
from src.video_processor import VideoProcessor
from src.resource_monitor import ResourceMonitor


def main():
    config = load_config()
    stop_event = Event()
    resource_monitor: ResourceMonitor | None = None

    def start_processing():
        nonlocal resource_monitor
        gui.update_status("Processing...")
        resource_monitor = ResourceMonitor(
            callback=lambda c, r, g, e: gui.update_resources(c, r, g, e),
            interval=config.monitor_interval,
            use_gpu=config.use_gpu,
        )
        resource_monitor.start()
        processor = VideoProcessor(
            config.video_path,
            config.output_text_path,
            update_callback=lambda frame, prog: (
                gui.show_frame(frame),
                gui.update_progress(prog),
                gui.update_status(f"{prog:.2f}%"),
                resource_monitor.update_progress(prog) if resource_monitor else None,
            ),
            stop_event=stop_event,
        )
        processor.process()
        if resource_monitor:
            resource_monitor.stop()
        gui.update_status("Completed")

    root = tk.Tk()
    gui = AppGUI(root, on_start=start_processing)

    def on_close():
        stop_event.set()
        if resource_monitor:
            resource_monitor.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
