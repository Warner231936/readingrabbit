"""Entry point for ReadingRabbit application."""
from __future__ import annotations

import threading
import tkinter as tk
from threading import Event
from typing import Optional

from src.config import load_config
from src.logger import setup_logging
from src.gui import AppGUI
from src.resource_monitor import ResourceMonitor
from src.video_processor import VideoProcessor


def main() -> None:
    config = load_config()
    logger = setup_logging(config.log_path, config.log_level)
    logger.info("Starting ReadingRabbit")
    stop_event = Event()
    pause_event = Event()
    monitor_thread: Optional[threading.Thread] = None
    monitor: Optional[ResourceMonitor] = None
    closing = False

    root = tk.Tk()

    def handle_alert(metric: str, value: float) -> None:
        message = f"{metric.upper()} usage reached {value:.1f}%"
        logger.warning("Resource alert: %s", message)
        gui.show_alert(message)

    def toggle_monitor(active: bool) -> None:
        if active:
            pause_event.clear()
        else:
            pause_event.set()

    def start_processing() -> None:
        nonlocal monitor_thread, monitor
        stop_event.clear()
        pause_event.clear()
        gui.prepare_for_run()

        if config.show_resource_usage:
            monitor = ResourceMonitor(
                update_callback=gui.update_resources,
                interval=config.monitor_interval,
                stop_event=stop_event,
                pause_event=pause_event,
                gpu_index=config.gpu_index if config.use_gpu else None,
                log_path=config.resource_log_path,
                alert_thresholds=config.resource_alerts,
                alert_callback=handle_alert,
                alert_cooldown=config.alert_cooldown_seconds,
                summary_path=config.resource_summary_path,
                alert_log_path=config.resource_alert_history_path,
                trend_window=config.analytics_trend_window,
            )
            monitor_thread = threading.Thread(target=monitor.run, daemon=True)
            monitor_thread.start()
        else:
            monitor = None
            monitor_thread = None

        processor = VideoProcessor(
            config=config,
            update_callback=lambda frame, progress, eta: (
                gui.show_frame(frame),
                gui.update_progress(progress),
                gui.update_status(f"Processing… {progress:.2f}%"),
                gui.update_eta(eta),
            ),
            stop_event=stop_event,
        )

        had_error = False
        cancelled = False
        try:
            processor.process()
            cancelled = stop_event.is_set()
            if not cancelled:
                gui.update_status("Completed")
                gui.update_eta(0.0)
        except Exception as exc:  # pragma: no cover - runtime path
            had_error = True
            if not stop_event.is_set():
                gui.show_error(str(exc))
                gui.update_status("Error")
        finally:
            already_cancelled = stop_event.is_set()
            stop_event.set()
            summary_text: Optional[str] = None
            summary_path: Optional[str] = None
            alert_log_path: Optional[str] = None
            if monitor_thread and monitor_thread.is_alive():
                monitor_thread.join(timeout=2.0)
            if monitor is not None:
                summary_text = monitor.summary_text
                summary_path = (
                    str(monitor.summary_path) if monitor.summary_path is not None else None
                )
                alert_log_path = (
                    str(monitor.alert_log_path)
                    if monitor.alert_log_path is not None
                    else None
                )
            monitor_thread = None
            monitor = None
            if not closing:
                if cancelled or already_cancelled:
                    if not had_error:
                        gui.update_status("Cancelled")
                        gui.update_eta(0.0)
                if summary_text:
                    gui.show_summary(summary_text, summary_path, alert_log_path)
                stop_event.clear()
                pause_event.clear()

    gui = AppGUI(
        root,
        on_start=start_processing,
        on_toggle_monitor=toggle_monitor if config.show_resource_usage else None,
        theme=config.theme(),
        show_resource_usage=config.show_resource_usage,
        history_seconds=config.resource_history_seconds,
        monitor_interval=config.monitor_interval,
        chart_height=config.resource_chart_height,
        resource_log_path=config.resource_log_path,
        resource_summary_path=config.resource_summary_path,
        resource_alert_history_path=config.resource_alert_history_path,
        layout=config.ui_layout,
        scaling=config.ui_scaling,
    )

    def on_close() -> None:
        nonlocal closing, monitor_thread
        closing = True
        stop_event.set()
        pause_event.clear()
        if monitor_thread and monitor_thread.is_alive():
            monitor_thread.join(timeout=2.0)
        logger.info("Shutting down ReadingRabbit")
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
