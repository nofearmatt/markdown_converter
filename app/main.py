# -*- coding: utf-8 -*-

import logging
import queue
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk
from app.app_logic import convert_files
from app.gui import AppGUI
from app.settings import load_settings, save_settings

# Настройка логирования для отладки
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MainApp:
    def __init__(self, root):
        self.root = root
        self.worker_thread = None
        self.progress_queue = queue.Queue() # Та самая "конвейерная лента"

        # Привязываем метод к кнопке закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Привязываем функции к кнопкам
        self.root.source_button.configure(command=self.select_source_dir)
        self.root.dest_button.configure(command=self.select_dest_dir)
        self.root.start_button.configure(command=self.start_conversion)

        # Запускаем периодическую проверку очереди сообщений от рабочего потока
        self.root.after(100, self.process_queue)

    def select_source_dir(self):
        dir_path = filedialog.askdirectory(title="Выберите папку с исходными файлами")
        if dir_path:
            self.root.source_entry.delete(0, 'end')
            self.root.source_entry.insert(0, dir_path)

    def select_dest_dir(self):
        dir_path = filedialog.askdirectory(title="Выберите папку для сохранения результатов")
        if dir_path:
            self.root.dest_entry.delete(0, 'end')
            self.root.dest_entry.insert(0, dir_path)

    def start_conversion(self):
        settings = self.root.get_current_settings()
        source_dir = settings["source_dir"]
        dest_dir = settings["dest_dir"]

        if not source_dir or not dest_dir:
            messagebox.showerror("Ошибка", "Пожалуйста, выберите папку-источник и папку-назначение.")
            return
            
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showwarning("Внимание", "Конвертация уже запущена.")
            return

        # Блокируем кнопку "Старт", чтобы избежать повторных запусков
        self.root.start_button.configure(state="disabled", text="В работе...")
        self.root.progress_bar.set(0)

        # Создаем и запускаем "Рабочего в цеху" (отдельный поток)
        self.worker_thread = threading.Thread(
            target=convert_files,
            args=(source_dir, dest_dir, settings, self.progress_queue),
            daemon=True # Поток завершится, если закроется основное приложение
        )
        self.worker_thread.start()

    def process_queue(self):
        """Обрабатывает сообщения из очереди от рабочего потока."""
        try:
            while not self.progress_queue.empty():
                message = self.progress_queue.get_nowait()
                
                if message["type"] == "status":
                    self.root.status_label.configure(text=message["message"])
                elif message["type"] == "progress":
                    progress_value = message["current"] / message["total"] if message["total"] > 0 else 0
                    self.root.progress_bar.set(progress_value)
                elif message["type"] == "done":
                    self.on_conversion_done(message["total"], message["errors"])
                # Можно добавить обработку ошибок, если нужно
                
        finally:
            # Перезапускаем проверку очереди через 100 мс
            self.root.after(100, self.process_queue)

    def on_conversion_done(self, total, errors):
        """Вызывается, когда конвертация завершена."""
        self.root.status_label.configure(text="Готов к работе.")
        self.root.start_button.configure(state="normal", text="Начать Конвертацию")
        
        if errors > 0:
            messagebox.showinfo("Завершено", f"Обработка завершена!\n\nВсего файлов: {total}\nФайлов с ошибками: {errors}")
        else:
            messagebox.showinfo("Завершено", f"Обработка завершена успешно!\n\nВсего файлов: {total}")

    def on_closing(self):
        """Вызывается при закрытии окна."""
        if self.worker_thread and self.worker_thread.is_alive():
            if messagebox.askyesno("Подтверждение", "Процесс конвертации еще не завершен. Вы уверены, что хотите выйти?"):
                self.save_and_destroy()
        else:
            self.save_and_destroy()

    def save_and_destroy(self):
        """Сохраняет настройки и закрывает приложение."""
        current_settings = self.root.get_current_settings()
        save_settings(current_settings)
        self.root.destroy()

if __name__ == '__main__':
    # Устанавливаем тему оформления
    ctk.set_appearance_mode("System") # System, Dark, Light
    ctk.set_default_color_theme("blue")

    # Загружаем настройки и создаем GUI
    initial_settings = load_settings()
    app_window = AppGUI(settings=initial_settings)
    
    # Запускаем логику приложения
    main_app_logic = MainApp(app_window)
    
    # Запускаем главный цикл окна
    app_window.mainloop()