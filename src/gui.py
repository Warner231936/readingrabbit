
"""Tkinter-based GUI for ReadingRabbit OCR."""
from __future__ import annotations

import os
import sys
import threading
import time
import tkinter as tk
import webbrowser
from collections import deque
from copy import deepcopy
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any, Callable, Mapping, Optional

import cv2
from PIL import Image, ImageTk


DEFAULT_THEME: dict[str, Any] = {
    "background": "#0b0c10",
    "surface": "#1f2833",
    "accent": "#45a29e",
    "text": "#c5c6c7",
    "highlight": "#66fcf1",
    "danger": "#ff6b6b",
    "font": "Segoe UI",
    "font_size": 11,
    "chart_colors": {
        "cpu": "#66fcf1",
        "ram": "#45a29e",
        "gpu": "#ff9f1c",
        "vram": "#f15bb5",
    },
}


def build_theme(custom_theme: Mapping[str, Any] | None) -> dict[str, Any]:
    """Merge user-specified theme settings with defaults."""

    theme = deepcopy(DEFAULT_THEME)
    if not custom_theme:
        return theme

    chart_colors = theme.get("chart_colors", {}).copy()
    for key, value in custom_theme.items():
        if key == "chart_colors" and isinstance(value, Mapping):
            chart_colors.update(value)  # type: ignore[arg-type]
        else:
            theme[key] = value
    theme["chart_colors"] = chart_colors
    return theme


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


class ResourceHistoryCanvas(tk.Canvas):
    """Simple line chart to display historical resource usage."""

    def __init__(
        self,
        master: tk.Misc,
        history_seconds: int,
        monitor_interval: float,
        theme: dict[str, Any],
        *,
        width: int = 420,
        height: int = 160,
    ) -> None:
        self.theme = theme
        self.history_seconds = max(history_seconds, 10)
        self.monitor_interval = monitor_interval if monitor_interval > 0 else 1.0
        self.max_points = max(2, int(round(self.history_seconds / self.monitor_interval)))
        self.font_family: str = theme.get("font", "Segoe UI")
        self.font_size: int = int(theme.get("font_size", 11))

        super().__init__(
            master,
            width=width,
            height=height,
            bg=theme.get("surface", DEFAULT_THEME["surface"]),
            highlightthickness=0,
        )

        chart_colors = theme.get("chart_colors", {})
        self.series = {
            "cpu": {
                "label": "CPU",
                "color": chart_colors.get("cpu", DEFAULT_THEME["chart_colors"]["cpu"]),
                "data": deque(maxlen=self.max_points),
            },
            "ram": {
                "label": "RAM",
                "color": chart_colors.get("ram", DEFAULT_THEME["chart_colors"]["ram"]),
                "data": deque(maxlen=self.max_points),
            },
            "gpu": {
                "label": "GPU",
                "color": chart_colors.get("gpu", DEFAULT_THEME["chart_colors"]["gpu"]),
                "data": deque(maxlen=self.max_points),
            },
            "vram": {
                "label": "VRAM",
                "color": chart_colors.get("vram", DEFAULT_THEME["chart_colors"]["vram"]),
                "data": deque(maxlen=self.max_points),
            },
        }

    def add_sample(
        self,
        cpu: float,
        gpu: Optional[float],
        gpu_mem: Optional[float],
        ram: float,
    ) -> None:
        self.series["cpu"]["data"].append(_clamp(cpu))
        self.series["ram"]["data"].append(_clamp(ram))
        self.series["gpu"]["data"].append(None if gpu is None else _clamp(gpu))
        self.series["vram"]["data"].append(None if gpu_mem is None else _clamp(gpu_mem))
        self._redraw()

    def clear(self) -> None:
        for series in self.series.values():
            series["data"].clear()
        self._redraw()

    def _redraw(self) -> None:
        width = int(float(self["width"]))
        height = int(float(self["height"]))
        margin = 16
        plot_height = height - (margin * 2)
        plot_width = width - (margin * 2)
        text_color = self.theme.get("text", DEFAULT_THEME["text"])
        background = self.theme.get("surface", DEFAULT_THEME["surface"])
        grid_color = self.theme.get("background", DEFAULT_THEME["background"])

        self.delete("all")
        self.create_rectangle(0, 0, width, height, fill=background, outline="")

        small_font = (self.font_family, max(8, self.font_size - 2))

        # Draw grid lines and labels
        for percent in range(0, 101, 25):
            y = height - margin - ((percent / 100) * plot_height)
            self.create_line(margin, y, width - margin, y, fill=grid_color, dash=(2, 4))
            self.create_text(
                width - margin + 6,
                y,
                text=f"{percent}%",
                anchor="w",
                fill=text_color,
                font=small_font,
            )

        sample_count = len(self.series["cpu"]["data"])
        if sample_count == 0:
            self.create_text(
                width / 2,
                height / 2,
                text="Waiting for samples…",
                fill=text_color,
                font=(self.font_family, self.font_size - 1),
            )
            return

        x_step = plot_width / max(sample_count - 1, 1)

        for key in ("cpu", "ram", "gpu", "vram"):
            series = self.series[key]
            values = list(series["data"])
            if not any(val is not None for val in values):
                continue
            coords: list[float] = []
            for idx, value in enumerate(values):
                if value is None:
                    if len(coords) >= 4:
                        self.create_line(
                            *coords,
                            fill=series["color"],
                            width=2,
                            smooth=True,
                        )
                    coords = []
                    continue
                x = margin + (idx * x_step)
                y = height - margin - ((value / 100) * plot_height)
                coords.extend([x, y])
            if len(coords) >= 4:
                self.create_line(
                    *coords,
                    fill=series["color"],
                    width=2,
                    smooth=True,
                )

        # Legend
        legend_x = margin
        legend_y = margin - 6
        for key in ("cpu", "ram", "gpu", "vram"):
            series = self.series[key]
            if not any(val is not None for val in series["data"]):
                continue
            self.create_rectangle(
                legend_x,
                legend_y,
                legend_x + 12,
                legend_y + 12,
                fill=series["color"],
                outline=series["color"],
            )
            self.create_text(
                legend_x + 16,
                legend_y + 6,
                text=series["label"],
                anchor="w",
                fill=text_color,
                font=small_font,
            )
            legend_x += 80

        span_seconds = min(
            self.history_seconds,
            (sample_count - 1) * self.monitor_interval,
        )
        self.create_text(
            margin,
            height - margin + 12,
            text=f"-{int(span_seconds)}s",
            anchor="w",
            fill=text_color,
            font=small_font,
        )
        self.create_text(
            width - margin,
            height - margin + 12,
            text="Now",
            anchor="e",
            fill=text_color,
            font=small_font,
        )


class AppGUI:
    def __init__(
        self,
        master: tk.Tk,
        on_start: Callable[[], None],
        on_toggle_monitor: Optional[Callable[[bool], None]] = None,
        *,
        theme: Optional[Mapping[str, Any]] = None,
        show_resource_usage: bool = True,
        history_seconds: int = 120,
        monitor_interval: float = 1.0,
        chart_height: int = 160,
        resource_log_path: Optional[str] = None,
        resource_summary_path: Optional[str] = None,
        resource_alert_history_path: Optional[str] = None,
        layout: str = "stacked",
        scaling: float = 1.0,
    ) -> None:
        self.master = master
        self._on_start = on_start
        self.on_toggle_monitor = on_toggle_monitor
        self.monitoring = True
        self.monitor_button: Optional[ttk.Button] = None
        self.show_resource_usage = show_resource_usage
        self._processing = False
        self._resource_placeholder = "CPU: --% | GPU: --% | VRAM: --% | RAM: --%"
        self._resource_log_path = Path(resource_log_path).expanduser() if resource_log_path else None
        self._resource_summary_path = (
            Path(resource_summary_path).expanduser() if resource_summary_path else None
        )
        self._alert_history_path = (
            Path(resource_alert_history_path).expanduser()
            if resource_alert_history_path
            else None
        )
        self.log_button: Optional[ttk.Button] = None
        self.summary_button: Optional[ttk.Button] = None
        self.alert_button: Optional[ttk.Button] = None
        self.summary_label: Optional[ttk.Label] = None
        self._layout = layout.lower()
        self._summary_placeholder = "Summary will appear after processing."

        self.theme = build_theme(theme)
        master.title("ReadingRabbit")
        master.configure(bg=self.theme["background"])
        try:
            master.tk.call("tk", "scaling", float(max(0.5, scaling)))
        except Exception:
            pass

        style = ttk.Style(master)
        style.theme_use("clam")
        style.configure("TFrame", background=self.theme["background"])
        style.configure(
            "TLabel",
            background=self.theme["background"],
            foreground=self.theme["text"],
            font=(self.theme["font"], self.theme["font_size"]),
        )
        style.configure(
            "Status.TLabel",
            background=self.theme["background"],
            foreground=self.theme["highlight"],
            font=(self.theme["font"], self.theme["font_size"]),
        )
        style.configure(
            "Resources.TLabel",
            background=self.theme["background"],
            foreground=self.theme["text"],
            font=(self.theme["font"], max(9, self.theme["font_size"] - 1)),
        )
        style.configure(
            "Alert.TLabel",
            background=self.theme["background"],
            foreground=self.theme["danger"],
            font=(self.theme["font"], max(10, self.theme["font_size"])),
        )
        style.configure(
            "TButton",
            background=self.theme["surface"],
            foreground=self.theme["text"],
            font=(self.theme["font"], self.theme["font_size"]),
        )
        style.map(
            "TButton",
            background=[("active", self.theme["accent"])],
            foreground=[("active", self.theme["background"])],
        )
        style.configure(
            "Horizontal.TProgressbar",
            troughcolor=self.theme["surface"],
            background=self.theme["accent"],
            thickness=20,
        )

        container = ttk.Frame(master, padding=20)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        if self._layout == "compact":
            main_frame = ttk.Frame(container)
            side_frame = ttk.Frame(container)
            main_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
            side_frame.grid(row=0, column=1, sticky="nsew")
            container.columnconfigure(0, weight=3)
            container.columnconfigure(1, weight=2)
            container.rowconfigure(0, weight=1)
            self._build_main_panel(main_frame)
            self._build_side_panel(
                side_frame,
                show_resource_usage,
                history_seconds,
                monitor_interval,
                chart_height,
            )
        else:
            main_frame = ttk.Frame(container)
            main_frame.grid(row=0, column=0, sticky="nsew")
            self._build_stacked_panel(
                main_frame,
                show_resource_usage,
                history_seconds,
                monitor_interval,
                chart_height,
            )

    def _build_main_panel(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)

        self.video_label = ttk.Label(parent, style="TLabel")
        self.video_label.grid(row=0, column=0, pady=(0, 12))

        self.progress = ttk.Progressbar(
            parent,
            orient="horizontal",
            length=420,
            mode="determinate",
        )
        self.progress.grid(row=1, column=0, sticky="ew", pady=6)

        self.status_label = ttk.Label(parent, text="Idle", style="Status.TLabel")
        self.status_label.grid(row=2, column=0, sticky="w", pady=6)

        self.start_button = ttk.Button(parent, text="Start", command=self._on_start_clicked)
        self.start_button.grid(row=3, column=0, sticky="ew", pady=(12, 0))

    def _build_side_panel(
        self,
        parent: ttk.Frame,
        show_resource_usage: bool,
        history_seconds: int,
        monitor_interval: float,
        chart_height: int,
    ) -> None:
        parent.columnconfigure(0, weight=1)

        resources_text = self._resource_placeholder
        if not show_resource_usage:
            resources_text = "Resource monitoring disabled in config."
        self.resources_label = ttk.Label(
            parent,
            text=resources_text,
            style="Resources.TLabel",
            wraplength=360,
            justify="left",
        )
        self.resources_label.grid(row=0, column=0, sticky="w", pady=6)

        self.history_canvas: Optional[ResourceHistoryCanvas] = None
        row = 1
        if show_resource_usage:
            self.history_canvas = ResourceHistoryCanvas(
                parent,
                history_seconds=history_seconds,
                monitor_interval=monitor_interval,
                theme=self.theme,
                height=chart_height,
            )
            self.history_canvas.grid(row=row, column=0, sticky="ew", pady=(6, 12))
            row += 1

        self.eta_label = ttk.Label(parent, text="ETA: 00:00:00", style="Resources.TLabel")
        self.eta_label.grid(row=row, column=0, sticky="w", pady=(6, 12))
        row += 1

        self.alert_label = ttk.Label(parent, text="", style="Alert.TLabel")
        self.alert_label.grid(row=row, column=0, sticky="w", pady=(0, 12))
        row += 1

        self.summary_label = ttk.Label(
            parent,
            text=self._summary_placeholder,
            style="Resources.TLabel",
            wraplength=360,
            justify="left",
        )
        self.summary_label.grid(row=row, column=0, sticky="w", pady=(0, 12))
        row += 1

        if self.on_toggle_monitor is not None and show_resource_usage:
            self.monitor_button = ttk.Button(
                parent,
                text="Pause Monitor",
                command=self._toggle_monitor,
            )
            self.monitor_button.grid(row=row, column=0, sticky="ew", pady=(0, 12))
            row += 1

        if self._resource_log_path is not None and show_resource_usage:
            self.log_button = self._create_open_button(
                parent,
                "Open Resource Log",
                self._open_resource_log,
                row,
            )
            row += 1

        if self._resource_summary_path is not None:
            self.summary_button = self._create_open_button(
                parent,
                "Open Resource Summary",
                self._open_resource_summary,
                row,
            )
            row += 1

        if self._alert_history_path is not None:
            self.alert_button = self._create_open_button(
                parent,
                "Open Alert History",
                self._open_alert_history,
                row,
            )

    def _build_stacked_panel(
        self,
        parent: ttk.Frame,
        show_resource_usage: bool,
        history_seconds: int,
        monitor_interval: float,
        chart_height: int,
    ) -> None:
        top = ttk.Frame(parent)
        top.pack(fill="x")
        bottom = ttk.Frame(parent)
        bottom.pack(fill="both", expand=True, pady=(12, 0))
        self._build_main_panel(top)
        self._build_side_panel(
            bottom,
            show_resource_usage,
            history_seconds,
            monitor_interval,
            chart_height,
        )

    def _create_open_button(
        self,
        parent: ttk.Frame,
        text: str,
        command: Callable[[], None],
        row: int,
    ) -> ttk.Button:
        button = ttk.Button(parent, text=text, command=command)
        button.state(["disabled"])
        button.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        return button

    def _on_start_clicked(self) -> None:
        if self._processing:
            return
        self._processing = True
        self.set_processing_state(True)
        threading.Thread(target=self._run_start_callback, daemon=True).start()

    def _run_start_callback(self) -> None:
        try:
            self._on_start()
        finally:
            self.master.after(0, self._on_processing_finished)

    def _on_processing_finished(self) -> None:
        self._processing = False
        self.set_processing_state(False)

    def set_processing_state(self, active: bool) -> None:
        def update() -> None:
            if active:
                self.start_button.state(["disabled"])
                self.start_button.config(text="Processing…")
            else:
                self.start_button.state(["!disabled"])
                self.start_button.config(text="Start")

        self.master.after(0, update)

    def prepare_for_run(self) -> None:
        self.clear_alert()
        self.reset_resources()
        self.update_status("Initializing…")
        self.update_progress(0.0)
        self.update_eta(0.0)
        self.clear_summary()
        if self.history_canvas is not None:
            self.master.after(0, self.history_canvas.clear)
        if self.monitor_button is not None:
            def _reset_button() -> None:
                self.monitoring = True
                self.monitor_button.config(text="Pause Monitor")

            self.master.after(0, _reset_button)

    def reset_resources(self) -> None:
        def update() -> None:
            self.resources_label.configure(text=self._resource_placeholder)

        self.master.after(0, update)

    def clear_alert(self) -> None:
        def update() -> None:
            self.alert_label.configure(text="")

        self.master.after(0, update)

    def clear_summary(self) -> None:
        def update() -> None:
            if self.summary_label is not None:
                self.summary_label.configure(text=self._summary_placeholder)
            if self.summary_button is not None:
                self.summary_button.state(["disabled"])
            if self.alert_button is not None:
                self.alert_button.state(["disabled"])

        self.master.after(0, update)

    def update_progress(self, value: float) -> None:
        def update() -> None:
            self.progress["value"] = max(0.0, min(100.0, value))

        self.master.after(0, update)

    def update_status(self, text: str) -> None:
        self.master.after(0, lambda: self.status_label.configure(text=text))

    def update_resources(
        self,
        cpu: float,
        gpu: Optional[float],
        gpu_mem: Optional[float],
        ram: float,
    ) -> None:
        def update() -> None:
            gpu_text = "N/A" if gpu is None else f"{gpu:.1f}%"
            vram_text = "N/A" if gpu_mem is None else f"{gpu_mem:.1f}%"
            self.resources_label.configure(
                text=(
                    f"CPU: {cpu:.1f}% | GPU: {gpu_text} | VRAM: {vram_text} | RAM: {ram:.1f}%"
                )
            )
            if self.history_canvas is not None:
                self.history_canvas.add_sample(cpu, gpu, gpu_mem, ram)
            if self._resource_log_path is not None and self.log_button is not None:
                if self._resource_log_path.exists():
                    self.log_button.state(["!disabled"])
                else:
                    self.log_button.state(["disabled"])

        self.master.after(0, update)

    def update_eta(self, seconds: float) -> None:
        def update() -> None:
            total_seconds = max(0, int(seconds))
            eta_str = time.strftime("%H:%M:%S", time.gmtime(total_seconds))
            self.eta_label.configure(text=f"ETA: {eta_str}")

        self.master.after(0, update)

    def show_frame(self, frame) -> None:
        if frame is None:
            return

        def update() -> None:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb)
            imgtk = ImageTk.PhotoImage(image=image)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

        self.master.after(0, update)

    def show_error(self, text: str) -> None:
        self.master.after(0, lambda: messagebox.showerror("ReadingRabbit Error", text))

    def show_alert(self, text: str) -> None:
        def update() -> None:
            self.alert_label.configure(text=f"Alert: {text}")
            messagebox.showwarning("ReadingRabbit Alert", text)

        self.master.after(0, update)

    def show_summary(
        self,
        text: str,
        summary_path: Optional[str],
        alert_log_path: Optional[str],
    ) -> None:
        def update() -> None:
            if self.summary_label is not None:
                self.summary_label.configure(text=text)
            if summary_path:
                path = Path(summary_path).expanduser()
                self._resource_summary_path = path
                if self.summary_button is not None and path.exists():
                    self.summary_button.state(["!disabled"])
            if alert_log_path:
                path = Path(alert_log_path).expanduser()
                self._alert_history_path = path
                if self.alert_button is not None and path.exists():
                    self.alert_button.state(["!disabled"])
            messagebox.showinfo("Resource Summary", text)

        self.master.after(0, update)

    def _toggle_monitor(self) -> None:
        self.monitoring = not self.monitoring
        if self.monitor_button:
            self.monitor_button["text"] = (
                "Resume Monitor" if not self.monitoring else "Pause Monitor"
            )
        if self.on_toggle_monitor:
            self.on_toggle_monitor(self.monitoring)

    def _open_resource_log(self) -> None:
        if self._resource_log_path is None:
            return
        self._open_path(self._resource_log_path, "Resource Log")

    def _open_resource_summary(self) -> None:
        if self._resource_summary_path is None:
            return
        self._open_path(self._resource_summary_path, "Resource Summary")

    def _open_alert_history(self) -> None:
        if self._alert_history_path is None:
            return
        self._open_path(self._alert_history_path, "Alert History")

    def _open_path(self, path: Path, description: str) -> None:
        if not path.exists():
            messagebox.showinfo(
                description,
                f"The file will be created at: {path.resolve()}",
            )
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            else:
                webbrowser.open(path.resolve().as_uri())
        except Exception as exc:  # pragma: no cover - platform specific
            messagebox.showerror(description, f"Unable to open file: {exc}")


