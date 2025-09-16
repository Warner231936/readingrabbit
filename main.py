"""Entry point for ReadingRabbit application."""
from __future__ import annotations

import threading
import tkinter as tk
from threading import Event
from typing import Optional

from src.config import load_config
from src.gui import AppGUI
from src.resource_monitor import ResourceMonitor
from src.video_processor import VideoProcessor


def main():
    config = load_config()
    stop_event = Event()
    monitor_pause_event = Event()
    monitor_thread: Optional[threading.Thread] = None
    closing = False

    def toggle_monitor(active: bool) -> None:
        if active:
            monitor_pause_event.clear()
        else:
            monitor_pause_event.set()

    def start_processing():
        nonlocal monitor_thread
        stop_event.clear()
        monitor_pause_event.clear()
        gui.update_status("Processing...")
        if config.show_resource_usage:
            monitor = ResourceMonitor(
                update_callback=gui.update_resources,
                interval=config.monitor_interval,
                stop_event=stop_event,
                pause_event=monitor_pause_event,
                gpu_index=config.gpu_index,
            )
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
            if not closing:
                gui.update_status("Completed")
        except Exception as exc:
            if not closing:
                gui.show_error(str(exc))
                gui.update_status("Error")
        finally:
            if config.show_resource_usage and monitor_thread and monitor_thread.is_alive():
                stop_event.set()
                monitor_thread.join(timeout=2.0)
                monitor_thread = None
            if not closing:
                stop_event.clear()

    root = tk.Tk()
    selected_theme = config.themes.get(config.ui_theme)
    gui = AppGUI(
        root,
        on_start=start_processing,
        on_toggle_monitor=toggle_monitor if config.show_resource_usage else None,
        theme=selected_theme,
        show_resource_usage=config.show_resource_usage,
        history_seconds=config.resource_history_seconds,
        monitor_interval=config.monitor_interval,
        chart_height=config.resource_chart_height,
    )
    
    def on_close() -> None:
        nonlocal monitor_thread, closing
        closing = True
        stop_event.set()
        if monitor_thread and monitor_thread.is_alive():
            monitor_thread.join(timeout=2.0)
            monitor_thread = None
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
