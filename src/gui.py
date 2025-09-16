"""Tkinter-based GUI for ReadingRabbit OCR."""
from __future__ import annotations

import threading
import time
import tkinter as tk
from collections import deque
from copy import deepcopy
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
        height: int = 140,
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

        # Determine total samples and axis labels
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
                        self.create_line(*coords, fill=series["color"], width=2, smooth=True)
                    coords = []
                    continue
                x = margin + (idx * x_step)
                y = height - margin - ((value / 100) * plot_height)
                coords.extend([x, y])
            if len(coords) >= 4:
                self.create_line(*coords, fill=series["color"], width=2, smooth=True)

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
        chart_height: int = 140,
    ) -> None:
        self.master = master
        self._on_start = on_start
        self.on_toggle_monitor = on_toggle_monitor
        self.monitoring = True
        self.monitor_button: Optional[ttk.Button] = None
        self.show_resource_usage = show_resource_usage
        self._processing = False

        self.theme = build_theme(theme)
        master.title("ReadingRabbit")
        master.configure(bg=self.theme["background"])

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

        self.video_label = ttk.Label(container, style="TLabel")
        self.video_label.pack(padx=10, pady=(0, 12))

        self.progress = ttk.Progressbar(
            container,
            orient="horizontal",
            length=420,
            mode="determinate",
        )
        self.progress.pack(padx=10, pady=6)

        self.status_label = ttk.Label(container, text="Idle", style="Status.TLabel")
        self.status_label.pack(padx=10, pady=6)

        resources_text = "CPU: --% | GPU: --% | VRAM: --% | RAM: --%"
        if not show_resource_usage:
            resources_text = "Resource monitoring disabled in config."
        self.resources_label = ttk.Label(
            container,
            text=resources_text,
            style="Resources.TLabel",
        )
        self.resources_label.pack(padx=10, pady=6)

        self.history_canvas: Optional[ResourceHistoryCanvas] = None
        if show_resource_usage:
            self.history_canvas = ResourceHistoryCanvas(
                container,
                history_seconds=history_seconds,
                monitor_interval=monitor_interval,
                theme=self.theme,
                height=chart_height,
            )
            self.history_canvas.pack(padx=10, pady=(6, 12))

        self.eta_label = ttk.Label(container, text="ETA: --:--:--", style="Resources.TLabel")
        self.eta_label.pack(padx=10, pady=(6, 12))

        self.start_button = ttk.Button(container, text="Start", command=self._on_start_clicked)
        self.start_button.pack(padx=10, pady=(0, 12))

        if self.on_toggle_monitor is not None and show_resource_usage:
            self.monitor_button = ttk.Button(
                container,
                text="Pause Monitor",
                command=self._toggle_monitor,
            )
            self.monitor_button.pack(padx=10, pady=(0, 12))

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

    def update_progress(self, value: float) -> None:
        self.progress["value"] = value
        self.master.update_idletasks()

    def update_status(self, text: str) -> None:
        self.status_label["text"] = text
        self.master.update_idletasks()

    def show_frame(self, frame) -> None:
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)
        self.master.update_idletasks()

    def update_resources(
        self,
        cpu: float,
        gpu: Optional[float],
        gpu_mem: Optional[float],
        ram: float,
    ) -> None:
        gpu_text = "N/A"
        vram_text = "N/A"
        if gpu is not None:
            gpu_text = f"{gpu:.1f}%"
        if gpu_mem is not None:
            vram_text = f"{gpu_mem:.1f}%"
        self.resources_label["text"] = (
            f"CPU: {cpu:.1f}% | GPU: {gpu_text} | VRAM: {vram_text} | RAM: {ram:.1f}%"
        )
        if self.history_canvas is not None:
            self.history_canvas.add_sample(cpu, gpu, gpu_mem, ram)
        self.master.update_idletasks()

    def update_eta(self, seconds: float) -> None:
        eta_str = time.strftime("%H:%M:%S", time.gmtime(seconds)) if seconds else "00:00:00"
        self.eta_label["text"] = f"ETA: {eta_str}"
        self.master.update_idletasks()

    def show_error(self, text: str) -> None:
        messagebox.showerror("ReadingRabbit Error", text)

    def _toggle_monitor(self) -> None:
        self.monitoring = not self.monitoring
        if self.monitor_button:
            self.monitor_button["text"] = (
                "Resume Monitor" if not self.monitoring else "Pause Monitor"
            )
        if self.on_toggle_monitor:
            self.on_toggle_monitor(self.monitoring)
