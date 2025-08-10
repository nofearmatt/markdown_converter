# -*- coding: utf-8 -*-

import customtkinter as ctk
from tkinter import filedialog
import os

class AppGUI(ctk.CTk):
    def __init__(self, settings):
        super().__init__()

        self.settings = settings

        # --- Настройка основного окна ---
        self.title("AI Studio Converter")
        self.geometry("700x550")
        self.center_window()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # Позволяет области с чекбоксами расширяться

        # --- Фрейм для выбора путей ---
        path_frame = ctk.CTkFrame(self)
        path_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        path_frame.grid_columnconfigure(1, weight=1)

        # Источник
        ctk.CTkLabel(path_frame, text="Папка-источник:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.source_entry = ctk.CTkEntry(path_frame, width=350)
        self.source_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.source_button = ctk.CTkButton(path_frame, text="Выбрать...", width=100)
        self.source_button.grid(row=0, column=2, padx=10, pady=10)
        self.source_entry.insert(0, self.settings.get("source_dir", ""))

        # Назначение
        ctk.CTkLabel(path_frame, text="Папка-назначение:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.dest_entry = ctk.CTkEntry(path_frame, width=350)
        self.dest_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        self.dest_button = ctk.CTkButton(path_frame, text="Выбрать...", width=100)
        self.dest_button.grid(row=1, column=2, padx=10, pady=10)
        self.dest_entry.insert(0, self.settings.get("dest_dir", ""))

        # --- Фрейм для настроек конвертации ---
        options_frame = ctk.CTkFrame(self)
        options_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        ctk.CTkLabel(options_frame, text="Настройки экспорта:", font=ctk.CTkFont(weight="bold")).pack(pady=10)

        self.include_system_prompt_var = ctk.BooleanVar(value=self.settings.get("include_system_prompt", True))
        self.include_run_settings_var = ctk.BooleanVar(value=self.settings.get("include_run_settings", True))
        self.exclude_thoughts_var = ctk.BooleanVar(value=self.settings.get("exclude_thoughts", True))

        ctk.CTkCheckBox(options_frame, text="Включить системный промпт (systemInstruction)", variable=self.include_system_prompt_var).pack(anchor="w", padx=20, pady=5)
        ctk.CTkCheckBox(options_frame, text="Включить настройки модели (runSettings)", variable=self.include_run_settings_var).pack(anchor="w", padx=20, pady=5)
        ctk.CTkCheckBox(options_frame, text="Исключить 'мысли' модели (isThought: true)", variable=self.exclude_thoughts_var).pack(anchor="w", padx=20, pady=5)

        # --- Фрейм для управления и статуса ---
        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=2, column=0, padx=20, pady=20, sticky="nsew")
        control_frame.grid_columnconfigure(0, weight=1)

        self.start_button = ctk.CTkButton(control_frame, text="Начать Конвертацию", height=40, font=ctk.CTkFont(size=14, weight="bold"))
        self.start_button.pack(pady=20, padx=20, fill="x")

        self.status_label = ctk.CTkLabel(control_frame, text="Готов к работе.", text_color="gray")
        self.status_label.pack(pady=10)

        self.progress_bar = ctk.CTkProgressBar(control_frame)
        self.progress_bar.pack(pady=10, padx=20, fill="x")
        self.progress_bar.set(0)

    def center_window(self):
        """Центрирует окно приложения на экране."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry('{}x{}+{}+{}'.format(width, height, x, y))

    def get_current_settings(self):
        """Собирает текущие настройки из всех элементов интерфейса."""
        return {
            "source_dir": self.source_entry.get(),
            "dest_dir": self.dest_entry.get(),
            "include_system_prompt": self.include_system_prompt_var.get(),
            "include_run_settings": self.include_run_settings_var.get(),
            "exclude_thoughts": self.exclude_thoughts_var.get()
        }