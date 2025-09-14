"""Tkinter-based GUI for ReadingRabbit OCR."""
import threading
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
import time

import cv2
from PIL import Image, ImageTk


class AppGUI:
    def __init__(self, master: tk.Tk, on_start: Callable[[], None]):
        self.master = master
        master.title("ReadingRabbit")
        master.configure(bg="#0b0c10")
        style = ttk.Style(master)
        style.theme_use("clam")
        style.configure("TFrame", background="#0b0c10")
        style.configure("TLabel", background="#0b0c10", foreground="#66fcf1")
        style.configure("TButton", background="#1f2833", foreground="#c5c6c7")
        style.configure("Horizontal.TProgressbar", background="#45a29e")

        self.video_label = ttk.Label(master)
        self.video_label.pack(padx=10, pady=10)

        self.progress = ttk.Progressbar(master, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(padx=10, pady=10)

        self.status_label = ttk.Label(master, text="Idle")
        self.status_label.pack(padx=10, pady=10)

        self.resources_label = ttk.Label(master, text="CPU: --% | GPU: --% | RAM: --%")
        self.resources_label.pack(padx=10, pady=10)

        self.eta_label = ttk.Label(master, text="ETA: --:--:--")
        self.eta_label.pack(padx=10, pady=10)

        self.start_button = ttk.Button(
            master,
            text="Start",
            command=lambda: threading.Thread(target=on_start, daemon=True).start(),
        )
        self.start_button.pack(padx=10, pady=10)

    def update_progress(self, value: float):
        self.progress['value'] = value
        self.master.update_idletasks()

    def update_status(self, text: str):
        self.status_label['text'] = text
        self.master.update_idletasks()

    def show_frame(self, frame):
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)
        self.master.update_idletasks()

    def update_resources(self, cpu: float, gpu: Optional[float], ram: float):
        gpu_text = f"{gpu:.1f}%" if gpu is not None else "N/A"
        self.resources_label['text'] = f"CPU: {cpu:.1f}% | GPU: {gpu_text} | RAM: {ram:.1f}%"
        self.master.update_idletasks()

    def update_eta(self, seconds: float):
        eta_str = time.strftime('%H:%M:%S', time.gmtime(seconds)) if seconds else "00:00:00"
        self.eta_label['text'] = f"ETA: {eta_str}"
        self.master.update_idletasks()
