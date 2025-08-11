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
        self.root.title("AI Studio Converter - Конвертер в Markdown")
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
    
    def save_current_settings(self):
        """Сохраняет текущие настройки."""
        try:
            # Собираем настройки из интерфейса
            current_settings = {
                "source_dir": self.source_entry.get().strip(),
                "dest_dir": self.dest_entry.get().strip(),
                "include_metadata": self.include_metadata_var.get(),
                # Временные метки отключены глобально
                "include_timestamps": False,
                "include_system_prompt": self.include_system_prompt_var.get(),
                "overwrite_existing": self.overwrite_existing_var.get(),
                "create_subfolders": self.create_subfolders_var.get(),
                "include_json_structure": self.include_json_structure_var.get(),
                "add_file_headers": self.add_file_headers_var.get()
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
            # Временные метки отключены глобально
            "include_timestamps": False,
            "include_system_prompt": self.include_system_prompt_var.get(),
            "overwrite_existing": self.overwrite_existing_var.get(),
            "create_subfolders": self.create_subfolders_var.get(),
            "include_json_structure": self.include_json_structure_var.get(),
            "add_file_headers": self.add_file_headers_var.get()
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
            # Сохраняем текущие настройки перед закрытием
            self.save_current_settings()
        except:
            pass
        
        # Закрываем окно
        self.root.destroy()
    
    def show(self):
        """Показывает главное окно."""
        self.root.mainloop()
