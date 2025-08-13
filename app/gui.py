# -*- coding: utf-8 -*-
"""
Модуль графического интерфейса для приложения AI Studio Converter.
Использует CustomTkinter для создания современного и красивого интерфейса.
"""

import os
import threading
import queue
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Dict, Any
import customtkinter as ctk
from pathlib import Path

from app.app_logic import convert_files
from app.settings import load_settings, save_settings
from app.watcher import DirectoryWatcher

class MainWindow:
    """
    Главное окно приложения AI Studio Converter.
    """
    
    def __init__(self, settings: Dict[str, Any]):
        """
        Инициализирует главное окно приложения.
        
        Args:
            settings: Словарь с настройками приложения
        """
        self.settings = settings
        self.progress_queue = queue.Queue()
        self.watcher = None
        
        # Настройка CustomTkinter
        ctk.set_appearance_mode("dark")  # Темная тема
        ctk.set_default_color_theme("blue")  # Синяя цветовая схема
        # Делаем интерфейс компактнее
        try:
            ctk.set_window_scaling(0.85)
            ctk.set_widget_scaling(0.85)
        except Exception:
            pass
        
        # Создание главного окна
        self.root = ctk.CTk()
        self.root.title("AI Studio Converter - Конвертер в Markdown/HTML")
        # Более компактное окно
        self.root.geometry("900x560")
        self.root.resizable(True, True)

        # Иконка окна (если есть)
        try:
            from pathlib import Path as _P
            project_root = _P(__file__).resolve().parent.parent
            icon_path = project_root / "assets" / "icon.ico"
            if icon_path.exists():
                # Для Windows .ico
                self.root.iconbitmap(str(icon_path))
        except Exception:
            pass
        
        # Центрируем окно на экране
        self.center_window()
        
        # Создаем интерфейс
        self.create_widgets()
        
        # Запускаем обработчик очереди прогресса
        self.start_progress_handler()
        
        # Привязываем событие закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def center_window(self):
        """Центрирует окно на экране."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_widgets(self):
        """Создает все элементы интерфейса."""
        # Главный заголовок
        title_label = ctk.CTkLabel(
            self.root,
            text="AI Studio Converter",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=12)
        
        subtitle_label = ctk.CTkLabel(
            self.root,
            text="Конвертер JSON файлов AI Studio в Markdown",
            font=ctk.CTkFont(size=12)
        )
        subtitle_label.pack(pady=(0, 14))
        
        # Создаем основной контейнер
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Верхняя строка: две колонки (слева — выбор папок, справа — настройки)
        top_row = ctk.CTkFrame(main_frame)
        top_row.pack(fill="both", expand=False, padx=0, pady=(8, 8))

        left_col = ctk.CTkFrame(top_row)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 6))

        right_col = ctk.CTkFrame(top_row)
        right_col.pack(side="left", fill="both", expand=True, padx=(6, 0))

        # Секция выбора папок (слева)
        self.create_folder_selection_section(left_col)

        # Секция настроек (справа)
        self.create_settings_section(right_col)
        
        # Секция кнопок управления
        self.create_control_section(main_frame)
        
        # Секция прогресса и логов
        self.create_progress_section(main_frame)
    
    def create_folder_selection_section(self, parent):
        """Создает секцию выбора папок."""
        folder_frame = ctk.CTkFrame(parent)
        folder_frame.pack(fill="x", padx=12, pady=12)
        
        # Заголовок секции
        folder_title = ctk.CTkLabel(
            folder_frame,
            text="📁 Выбор папок",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        folder_title.pack(pady=(12, 8))
        
        # Исходная папка
        source_frame = ctk.CTkFrame(folder_frame)
        source_frame.pack(fill="x", padx=12, pady=8)
        
        source_label = ctk.CTkLabel(source_frame, text="Исходная папка с JSON файлами:")
        source_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        source_path_frame = ctk.CTkFrame(source_frame)
        source_path_frame.pack(fill="x", padx=8, pady=(0, 8))
        
        self.source_entry = ctk.CTkEntry(
            source_path_frame,
            placeholder_text="Выберите папку с JSON файлами AI Studio...",
            height=30
        )
        self.source_entry.pack(side="left", fill="x", expand=True, padx=(8, 8), pady=6)
        
        source_button = ctk.CTkButton(
            source_path_frame,
            text="Обзор",
            width=72,
            height=32,
            command=self.browse_source_folder
        )
        source_button.pack(side="right", padx=(0, 8), pady=6)
        
        # Папка назначения
        dest_frame = ctk.CTkFrame(folder_frame)
        dest_frame.pack(fill="x", padx=12, pady=8)
        
        dest_label = ctk.CTkLabel(dest_frame, text="Папка для сохранения Markdown файлов:")
        dest_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        dest_path_frame = ctk.CTkFrame(dest_frame)
        dest_path_frame.pack(fill="x", padx=8, pady=(0, 8))
        
        self.dest_entry = ctk.CTkEntry(
            dest_path_frame,
            placeholder_text="Выберите папку для сохранения результатов...",
            height=30
        )
        self.dest_entry.pack(side="left", fill="x", expand=True, padx=(8, 8), pady=6)
        
        dest_button = ctk.CTkButton(
            dest_path_frame,
            text="Обзор",
            width=72,
            height=32,
            command=self.browse_dest_folder
        )
        dest_button.pack(side="right", padx=(0, 8), pady=6)
        
        # Загружаем сохраненные пути
        self.source_entry.insert(0, self.settings.get("source_dir", ""))
        self.dest_entry.insert(0, self.settings.get("dest_dir", ""))
    
    def create_settings_section(self, parent):
        """Создает секцию настроек конвертации."""
        settings_frame = ctk.CTkFrame(parent)
        settings_frame.pack(fill="x", padx=12, pady=12)
        
        # Заголовок секции
        settings_title = ctk.CTkLabel(
            settings_frame,
            text="⚙️ Настройки конвертации",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        settings_title.pack(pady=(12, 8))
        
        # Создаем сетку для настроек
        settings_grid = ctk.CTkFrame(settings_frame)
        settings_grid.pack(fill="x", padx=12, pady=(0, 12))
        
        # Первая строка настроек
        row1 = ctk.CTkFrame(settings_grid)
        row1.pack(fill="x", pady=4)
        
        self.include_metadata_var = tk.BooleanVar(value=self.settings.get("include_metadata", True))
        metadata_checkbox = ctk.CTkCheckBox(
            row1,
            text="Включить метаданные",
            variable=self.include_metadata_var
        )
        metadata_checkbox.pack(side="left", padx=8, pady=6)
        
        # Чекбокс системной инструкции (вместо временных меток)
        self.include_system_prompt_var = tk.BooleanVar(value=self.settings.get("include_system_prompt", True))
        system_prompt_checkbox = ctk.CTkCheckBox(
            row1,
            text="Включить системную инструкцию",
            variable=self.include_system_prompt_var
        )
        system_prompt_checkbox.pack(side="left", padx=8, pady=6)
        
        # Вторая строка настроек
        row2 = ctk.CTkFrame(settings_grid)
        row2.pack(fill="x", pady=4)
        
        self.overwrite_existing_var = tk.BooleanVar(value=self.settings.get("overwrite_existing", False))
        overwrite_checkbox = ctk.CTkCheckBox(
            row2,
            text="Перезаписывать существующие файлы",
            variable=self.overwrite_existing_var
        )
        overwrite_checkbox.pack(side="left", padx=8, pady=6)
        
        self.create_subfolders_var = tk.BooleanVar(value=self.settings.get("create_subfolders", True))
        subfolders_checkbox = ctk.CTkCheckBox(
            row2,
            text="Создавать подпапки",
            variable=self.create_subfolders_var
        )
        subfolders_checkbox.pack(side="left", padx=8, pady=6)
        
        # Третья строка настроек
        row3 = ctk.CTkFrame(settings_grid)
        row3.pack(fill="x", pady=4)
        
        self.include_json_structure_var = tk.BooleanVar(value=self.settings.get("include_json_structure", False))
        json_structure_checkbox = ctk.CTkCheckBox(
            row3,
            text="Включить JSON структуру",
            variable=self.include_json_structure_var
        )
        json_structure_checkbox.pack(side="left", padx=8, pady=6)
        
        self.add_file_headers_var = tk.BooleanVar(value=self.settings.get("add_file_headers", True))
        headers_checkbox = ctk.CTkCheckBox(
            row3,
            text="Добавлять заголовки файлов",
            variable=self.add_file_headers_var
        )
        headers_checkbox.pack(side="left", padx=8, pady=6)

        # Четвертая строка: флаги рендера
        row4 = ctk.CTkFrame(settings_grid)
        row4.pack(fill="x", pady=4)

        self.include_run_settings_var = tk.BooleanVar(value=self.settings.get("include_run_settings", True))
        include_run_checkbox = ctk.CTkCheckBox(
            row4,
            text="Включить Run Settings",
            variable=self.include_run_settings_var
        )
        include_run_checkbox.pack(side="left", padx=8, pady=6)

        self.exclude_thoughts_var = tk.BooleanVar(value=self.settings.get("exclude_thoughts", True))
        exclude_thoughts_checkbox = ctk.CTkCheckBox(
            row4,
            text="Исключать мысли (thoughts)",
            variable=self.exclude_thoughts_var
        )
        exclude_thoughts_checkbox.pack(side="left", padx=8, pady=6)

        # Пятая строка: временные метки и YAML FM
        row5 = ctk.CTkFrame(settings_grid)
        row5.pack(fill="x", pady=4)

        self.include_timestamps_var = tk.BooleanVar(value=self.settings.get("include_timestamps", False))
        timestamps_checkbox = ctk.CTkCheckBox(
            row5,
            text="Включить временные метки",
            variable=self.include_timestamps_var
        )
        timestamps_checkbox.pack(side="left", padx=8, pady=6)

        self.enable_yaml_front_matter_var = tk.BooleanVar(value=self.settings.get("enable_yaml_front_matter", False))
        yaml_checkbox = ctk.CTkCheckBox(
            row5,
            text="YAML Front Matter",
            variable=self.enable_yaml_front_matter_var
        )
        yaml_checkbox.pack(side="left", padx=8, pady=6)

        # Шестая строка: dry-run и переименование
        row6 = ctk.CTkFrame(settings_grid)
        row6.pack(fill="x", pady=4)

        self.dry_run_var = tk.BooleanVar(value=self.settings.get("dry_run", False))
        dryrun_checkbox = ctk.CTkCheckBox(
            row6,
            text="Пробный запуск (dry-run)",
            variable=self.dry_run_var
        )
        dryrun_checkbox.pack(side="left", padx=8, pady=6)

        self.rename_extensionless_var = tk.BooleanVar(value=self.settings.get("rename_extensionless", False))
        rename_checkbox = ctk.CTkCheckBox(
            row6,
            text="Переименовывать файлы без расширения в .json",
            variable=self.rename_extensionless_var
        )
        rename_checkbox.pack(side="left", padx=8, pady=6)

        # Седьмая строка: форматы и воркеры
        row7 = ctk.CTkFrame(settings_grid)
        row7.pack(fill="x", pady=4)

        self.export_format_var = tk.StringVar(value=(self.settings.get("export_format") or "md").lower())
        export_label = ctk.CTkLabel(row7, text="Формат экспорта:")
        export_label.pack(side="left", padx=(8, 4), pady=6)
        export_menu = ctk.CTkOptionMenu(row7, values=["md", "html", "both"], variable=self.export_format_var)
        export_menu.pack(side="left", padx=(0, 12), pady=6)

        self.workers_var = tk.IntVar(value=int(self.settings.get("workers", 4)))
        workers_label = ctk.CTkLabel(row7, text="Потоков:")
        workers_label.pack(side="left", padx=(8, 4), pady=6)
        self.workers_slider = ctk.CTkSlider(row7, from_=1, to=16, number_of_steps=15, command=lambda v: self.workers_var.set(int(v)))
        self.workers_slider.set(float(self.workers_var.get()))
        self.workers_slider.pack(side="left", fill="x", expand=True, padx=(0, 12), pady=6)

        # Восьмая строка: шаблон Markdown
        row8 = ctk.CTkFrame(settings_grid)
        row8.pack(fill="x", pady=4)

        tpl_label = ctk.CTkLabel(row8, text="Шаблон Markdown (Jinja2):")
        tpl_label.pack(side="left", padx=(8, 4), pady=6)
        self.template_entry = ctk.CTkEntry(row8, placeholder_text="Путь к шаблону .j2 или .md", height=30)
        self.template_entry.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=6)
        if self.settings.get("template_path"):
            self.template_entry.insert(0, self.settings.get("template_path"))
        tpl_btn = ctk.CTkButton(row8, text="Выбрать", width=80, command=self.browse_template_file)
        tpl_btn.pack(side="left", padx=(0, 8), pady=6)

        # Девятая строка: шаблон HTML
        row9 = ctk.CTkFrame(settings_grid)
        row9.pack(fill="x", pady=4)

        htpl_label = ctk.CTkLabel(row9, text="Шаблон HTML (Jinja2):")
        htpl_label.pack(side="left", padx=(8, 4), pady=6)
        self.html_template_entry = ctk.CTkEntry(row9, placeholder_text="Путь к шаблону .html/.j2", height=30)
        self.html_template_entry.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=6)
        if self.settings.get("html_template_path"):
            self.html_template_entry.insert(0, self.settings.get("html_template_path"))
        htpl_btn = ctk.CTkButton(row9, text="Выбрать", width=80, command=self.browse_html_template_file)
        htpl_btn.pack(side="left", padx=(0, 8), pady=6)
    
    def create_control_section(self, parent):
        """Создает секцию кнопок управления."""
        control_frame = ctk.CTkFrame(parent)
        control_frame.pack(fill="x", padx=12, pady=12)
        
        # Кнопки управления
        button_frame = ctk.CTkFrame(control_frame)
        button_frame.pack(pady=8)
        
        # Кнопка конвертации
        self.convert_button = ctk.CTkButton(
            button_frame,
            text="🚀 Начать конвертацию",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            command=self.start_conversion
        )
        self.convert_button.pack(side="left", padx=8, pady=6)
        
        # Кнопка сохранения настроек
        save_button = ctk.CTkButton(
            button_frame,
            text="💾 Сохранить настройки",
            height=40,
            command=self.save_current_settings
        )
        save_button.pack(side="left", padx=8, pady=6)
        
        # Кнопка сброса настроек
        reset_button = ctk.CTkButton(
            button_frame,
            text="🔄 Сбросить настройки",
            height=40,
            command=self.reset_settings
        )
        reset_button.pack(side="left", padx=8, pady=6)

        # Кнопки наблюдателя
        watch_button_frame = ctk.CTkFrame(control_frame)
        watch_button_frame.pack(pady=4)

        self.watch_start_button = ctk.CTkButton(
            watch_button_frame,
            text="👁️ Запустить наблюдение",
            height=34,
            command=self.start_watching
        )
        self.watch_start_button.pack(side="left", padx=8, pady=4)

        self.watch_stop_button = ctk.CTkButton(
            watch_button_frame,
            text="🛑 Остановить наблюдение",
            height=34,
            command=self.stop_watching,
            state="disabled"
        )
        self.watch_stop_button.pack(side="left", padx=8, pady=4)
    
    def create_progress_section(self, parent):
        """Создает секцию прогресса и логов."""
        progress_frame = ctk.CTkFrame(parent)
        progress_frame.pack(fill="both", expand=True, padx=12, pady=12)
        
        # Заголовок секции
        progress_title = ctk.CTkLabel(
            progress_frame,
            text="📊 Прогресс и логи",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        progress_title.pack(pady=(12, 8))
        
        # Прогресс бар
        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(fill="x", padx=12, pady=(0, 8))
        self.progress_bar.set(0)
        
        # Статус
        self.status_label = ctk.CTkLabel(
            progress_frame,
            text="Готов к работе",
            font=ctk.CTkFont(size=11)
        )
        self.status_label.pack(pady=(0, 8))
        
        # Текстовое поле для логов
        log_frame = ctk.CTkFrame(progress_frame)
        log_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        
        log_label = ctk.CTkLabel(log_frame, text="Лог операций:")
        log_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Создаем текстовое поле с прокруткой
        text_frame = ctk.CTkFrame(log_frame)
        text_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        self.log_text = ctk.CTkTextbox(
            text_frame,
            wrap="word",
            font=ctk.CTkFont(size=10)
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        
        # Полоса прокрутки
        scrollbar = ctk.CTkScrollbar(text_frame, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # Кнопка очистки логов
        clear_log_button = ctk.CTkButton(
            log_frame,
            text="🧹 Очистить лог",
            height=30,
            command=self.clear_log
        )
        clear_log_button.pack(anchor="e", padx=10, pady=(0, 10))

        # Предпросмотр Markdown
        preview_frame = ctk.CTkFrame(parent)
        preview_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        preview_title = ctk.CTkLabel(preview_frame, text="🖼 Предпросмотр Markdown", font=ctk.CTkFont(size=14, weight="bold"))
        preview_title.pack(pady=(12, 8))
        path_row = ctk.CTkFrame(preview_frame)
        path_row.pack(fill="x", padx=12, pady=(0, 8))
        self.preview_path_entry = ctk.CTkEntry(path_row, placeholder_text="Выберите JSON файл для предпросмотра...", height=30)
        self.preview_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=6)
        browse_preview_btn = ctk.CTkButton(path_row, text="Обзор", width=80, command=self.browse_preview_file)
        browse_preview_btn.pack(side="left", padx=(0, 8), pady=6)
        render_btn = ctk.CTkButton(path_row, text="Рендер", width=100, command=self.render_preview)
        render_btn.pack(side="left", padx=(0, 8), pady=6)
        self.preview_text = ctk.CTkTextbox(preview_frame, wrap="word", font=ctk.CTkFont(size=10))
        self.preview_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))
    
    def browse_source_folder(self):
        """Открывает диалог выбора исходной папки."""
        folder = filedialog.askdirectory(
            title="Выберите папку с JSON файлами AI Studio"
        )
        if folder:
            self.source_entry.delete(0, tk.END)
            self.source_entry.insert(0, folder)
    
    def browse_dest_folder(self):
        """Открывает диалог выбора папки назначения."""
        folder = filedialog.askdirectory(
            title="Выберите папку для сохранения Markdown файлов"
        )
        if folder:
            self.dest_entry.delete(0, tk.END)
            self.dest_entry.insert(0, folder)
    
    def browse_preview_file(self):
        path = filedialog.askopenfilename(title="Выберите JSON файл", filetypes=[("JSON", "*.json"), ("All", "*.*")])
        if path:
            self.preview_path_entry.delete(0, tk.END)
            self.preview_path_entry.insert(0, path)
    
    def render_preview(self):
        try:
            json_path = self.preview_path_entry.get().strip()
            if not json_path or not os.path.exists(json_path):
                messagebox.showerror("Ошибка", "Выберите корректный JSON файл для предпросмотра")
                return
            settings = {
                "include_metadata": self.include_metadata_var.get(),
                "include_timestamps": self.include_timestamps_var.get(),
                "include_system_prompt": self.include_system_prompt_var.get(),
                "include_json_structure": self.include_json_structure_var.get(),
                "add_file_headers": self.add_file_headers_var.get(),
                "include_run_settings": self.include_run_settings_var.get(),
                "exclude_thoughts": self.exclude_thoughts_var.get(),
                "template_path": self.template_entry.get().strip(),
                "enable_yaml_front_matter": self.enable_yaml_front_matter_var.get(),
            }
            from app.app_logic import render_markdown_preview
            md_text = render_markdown_preview(json_path, settings)
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, md_text)
        except Exception as e:
            self.log_message(f"❌ Ошибка предпросмотра: {e}", "error")
            messagebox.showerror("Ошибка", f"Не удалось отрендерить предпросмотр: {e}")

    def browse_template_file(self):
        path = filedialog.askopenfilename(title="Выберите шаблон Markdown (Jinja2)", filetypes=[("Templates", "*.j2 *.md *.tmpl"), ("All", "*.*")])
        if path:
            self.template_entry.delete(0, tk.END)
            self.template_entry.insert(0, path)

    def browse_html_template_file(self):
        path = filedialog.askopenfilename(title="Выберите шаблон HTML (Jinja2)", filetypes=[("Templates", "*.html *.j2 *.tmpl"), ("All", "*.*")])
        if path:
            self.html_template_entry.delete(0, tk.END)
            self.html_template_entry.insert(0, path)
    
    def save_current_settings(self):
        """Сохраняет текущие настройки."""
        try:
            # Собираем настройки из интерфейса
            current_settings = {
                "source_dir": self.source_entry.get().strip(),
                "dest_dir": self.dest_entry.get().strip(),
                "include_metadata": self.include_metadata_var.get(),
                "include_timestamps": self.include_timestamps_var.get(),
                "include_system_prompt": self.include_system_prompt_var.get(),
                "overwrite_existing": self.overwrite_existing_var.get(),
                "create_subfolders": self.create_subfolders_var.get(),
                "include_json_structure": self.include_json_structure_var.get(),
                "add_file_headers": self.add_file_headers_var.get(),
                "include_run_settings": self.include_run_settings_var.get(),
                "exclude_thoughts": self.exclude_thoughts_var.get(),
                "dry_run": self.dry_run_var.get(),
                "rename_extensionless": self.rename_extensionless_var.get(),
                "workers": int(self.workers_var.get()),
                "export_format": self.export_format_var.get(),
                "template_path": self.template_entry.get().strip(),
                "html_template_path": self.html_template_entry.get().strip(),
                "enable_yaml_front_matter": self.enable_yaml_front_matter_var.get(),
            }
            
            # Сохраняем настройки
            if save_settings(current_settings):
                self.settings = current_settings
                self.log_message("✅ Настройки успешно сохранены", "info")
                messagebox.showinfo("Успех", "Настройки успешно сохранены!")
            else:
                self.log_message("❌ Ошибка при сохранении настроек", "error")
                messagebox.showerror("Ошибка", "Не удалось сохранить настройки!")
                
        except Exception as e:
            self.log_message(f"❌ Ошибка при сохранении настроек: {e}", "error")
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки: {e}")
    
    def reset_settings(self):
        """Сбрасывает настройки к значениям по умолчанию."""
        try:
            from app.settings import reset_settings
            if reset_settings():
                # Перезагружаем настройки
                self.settings = load_settings()
                
                # Обновляем интерфейс
                self.source_entry.delete(0, tk.END)
                self.dest_entry.delete(0, tk.END)
                
                self.include_metadata_var.set(True)
                self.include_system_prompt_var.set(True)
                self.overwrite_existing_var.set(False)
                self.create_subfolders_var.set(True)
                self.include_json_structure_var.set(False)
                self.add_file_headers_var.set(True)
                self.include_run_settings_var.set(True)
                self.exclude_thoughts_var.set(True)
                self.include_timestamps_var.set(False)
                self.enable_yaml_front_matter_var.set(False)
                self.dry_run_var.set(False)
                self.rename_extensionless_var.set(False)
                self.export_format_var.set("md")
                self.workers_var.set(4)
                self.workers_slider.set(4)
                self.template_entry.delete(0, tk.END)
                self.html_template_entry.delete(0, tk.END)
                
                self.log_message("🔄 Настройки сброшены к значениям по умолчанию", "info")
                messagebox.showinfo("Успех", "Настройки сброшены к значениям по умолчанию!")
            else:
                self.log_message("❌ Ошибка при сбросе настроек", "error")
                messagebox.showerror("Ошибка", "Не удалось сбросить настройки!")
                
        except Exception as e:
            self.log_message(f"❌ Ошибка при сбросе настроек: {e}", "error")
            messagebox.showerror("Ошибка", f"Не удалось сбросить настройки: {e}")
    
    def start_conversion(self):
        """Запускает процесс конвертации."""
        # Проверяем введенные данные
        source_dir = self.source_entry.get().strip()
        dest_dir = self.dest_entry.get().strip()
        
        if not source_dir or not dest_dir:
            messagebox.showerror("Ошибка", "Пожалуйста, выберите исходную папку и папку назначения!")
            return
        
        if not os.path.exists(source_dir):
            messagebox.showerror("Ошибка", "Исходная папка не существует!")
            return
        
        # Собираем настройки
        conversion_settings = {
            "source_dir": source_dir,
            "dest_dir": dest_dir,
            "include_metadata": self.include_metadata_var.get(),
            "include_timestamps": self.include_timestamps_var.get(),
            "include_system_prompt": self.include_system_prompt_var.get(),
            "overwrite_existing": self.overwrite_existing_var.get(),
            "create_subfolders": self.create_subfolders_var.get(),
            "include_json_structure": self.include_json_structure_var.get(),
            "add_file_headers": self.add_file_headers_var.get(),
            "include_run_settings": self.include_run_settings_var.get(),
            "exclude_thoughts": self.exclude_thoughts_var.get(),
            "dry_run": self.dry_run_var.get(),
            "rename_extensionless": self.rename_extensionless_var.get(),
            "workers": int(self.workers_var.get()),
            "export_format": self.export_format_var.get(),
            "template_path": self.template_entry.get().strip(),
            "html_template_path": self.html_template_entry.get().strip(),
            "enable_yaml_front_matter": self.enable_yaml_front_matter_var.get(),
        }
        
        # Отключаем кнопку конвертации
        self.convert_button.configure(state="disabled")
        self.convert_button.configure(text="🔄 Конвертация...")
        
        # Очищаем лог
        self.clear_log()
        
        # Логируем начало конвертации
        self.log_message("🚀 Начинаем конвертацию...", "info")
        self.log_message(f"📁 Исходная папка: {source_dir}", "info")
        self.log_message(f"📁 Папка назначения: {dest_dir}", "info")
        self.log_message("=" * 50, "info")
        
        # Запускаем конвертацию в отдельном потоке
        conversion_thread = threading.Thread(
            target=self.run_conversion,
            args=(conversion_settings,),
            daemon=True
        )
        conversion_thread.start()
    
    def run_conversion(self, settings):
        """Запускает конвертацию в отдельном потоке."""
        try:
            convert_files(
                source_dir=settings["source_dir"],
                dest_dir=settings["dest_dir"],
                settings=settings,
                progress_queue=self.progress_queue
            )
        except Exception as e:
            self.progress_queue.put({
                "type": "error",
                "message": f"Критическая ошибка: {e}"
            })
    
    def start_progress_handler(self):
        """Запускает обработчик очереди прогресса."""
        def check_queue():
            try:
                while True:
                    # Проверяем очередь без блокировки
                    message = self.progress_queue.get_nowait()
                    self.handle_progress_message(message)
            except queue.Empty:
                pass
            finally:
                # Планируем следующую проверку
                self.root.after(100, check_queue)
        
        # Запускаем первую проверку
        self.root.after(100, check_queue)
    
    def handle_progress_message(self, message):
        """Обрабатывает сообщения о прогрессе."""
        msg_type = message.get("type", "info")
        msg_text = message.get("message", "")
        
        if msg_type == "progress":
            # Обновляем прогресс бар
            progress_value = message.get("value", 0) / 100.0
            self.progress_bar.set(progress_value)
            self.status_label.configure(text=msg_text)
            self.log_message(f"📊 {msg_text}", "info")
            
        elif msg_type == "success":
            # Успешное завершение
            self.progress_bar.set(1.0)
            self.status_label.configure(text="Конвертация завершена успешно!")
            self.log_message(f"✅ {msg_text}", "success")
            self.convert_button.configure(state="normal", text="🚀 Начать конвертацию")
            
        elif msg_type == "warning":
            # Предупреждение
            self.log_message(f"⚠️ {msg_text}", "warning")
            
        elif msg_type == "error":
            # Ошибка
            self.log_message(f"❌ {msg_text}", "error")
            self.convert_button.configure(state="normal", text="🚀 Начать конвертацию")
            
        elif msg_type == "info":
            # Информационное сообщение
            self.log_message(f"ℹ️ {msg_text}", "info")
    
    def log_message(self, message, level="info"):
        """Добавляет сообщение в лог."""
        # Определяем цвет для разных уровней
        colors = {
            "info": "white",
            "success": "green",
            "warning": "orange",
            "error": "red"
        }
        
        color = colors.get(level, "white")
        
        # Добавляем временную метку
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        # Вставляем сообщение в конец текста
        self.log_text.insert(tk.END, formatted_message)
        
        # Прокручиваем к концу
        self.log_text.see(tk.END)
        
        # Обновляем интерфейс
        self.root.update_idletasks()
    
    def clear_log(self):
        """Очищает лог."""
        self.log_text.delete(1.0, tk.END)
        self.log_message("🧹 Лог очищен", "info")
    
    def on_closing(self):
        """Обработчик закрытия окна."""
        try:
            # Останавливаем наблюдатель, если он запущен
            if self.watcher is not None:
                self.watcher.stop()
                self.watcher = None
            # Сохраняем текущие настройки перед закрытием
            self.save_current_settings()
        except:
            pass
        
        # Закрываем окно
        self.root.destroy()
    
    def show(self):
        """Показывает главное окно."""
        self.root.mainloop()

    # Наблюдение за директорией
    def start_watching(self):
        source_dir = self.source_entry.get().strip()
        dest_dir = self.dest_entry.get().strip()
        if not source_dir or not dest_dir:
            messagebox.showerror("Ошибка", "Выберите исходную и целевую папки для наблюдения")
            return
        if not os.path.exists(source_dir):
            messagebox.showerror("Ошибка", "Исходная папка не существует")
            return
        # Используем текущие настройки из формы
        settings = {
            "source_dir": source_dir,
            "dest_dir": dest_dir,
            "include_metadata": self.include_metadata_var.get(),
            "include_timestamps": self.include_timestamps_var.get(),
            "include_system_prompt": self.include_system_prompt_var.get(),
            "overwrite_existing": self.overwrite_existing_var.get(),
            "create_subfolders": self.create_subfolders_var.get(),
            "include_json_structure": self.include_json_structure_var.get(),
            "add_file_headers": self.add_file_headers_var.get(),
            "include_run_settings": self.include_run_settings_var.get(),
            "exclude_thoughts": self.exclude_thoughts_var.get(),
            "dry_run": self.dry_run_var.get(),
            "rename_extensionless": self.rename_extensionless_var.get(),
            "workers": int(self.workers_var.get()),
            "export_format": self.export_format_var.get(),
            "template_path": self.template_entry.get().strip(),
            "html_template_path": self.html_template_entry.get().strip(),
            "enable_yaml_front_matter": self.enable_yaml_front_matter_var.get(),
        }
        self.watcher = DirectoryWatcher(source_dir, dest_dir, settings, self.progress_queue)
        self.watcher.start()
        self.watch_start_button.configure(state="disabled")
        self.watch_stop_button.configure(state="normal")
        self.status_label.configure(text="Наблюдение запущено")

    def stop_watching(self):
        if self.watcher is not None:
            try:
                self.watcher.stop()
            finally:
                self.watcher = None
        self.watch_start_button.configure(state="normal")
        self.watch_stop_button.configure(state="disabled")
        self.status_label.configure(text="Наблюдение остановлено")
