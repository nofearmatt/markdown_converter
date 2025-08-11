# -*- coding: utf-8 -*-
"""
Главный модуль приложения AI Studio Converter.
Запускает GUI интерфейс для конвертации JSON файлов AI Studio в Markdown.
"""

import sys
import os
import logging
from pathlib import Path

# Добавляем папку app в путь для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.app_logic import convert_files
from app.settings import load_settings, save_settings

def setup_logging():
    """
    Настраивает систему логирования для приложения.
    """
    # Создаем папку для логов в %APPDATA%/AIStudioConverter/logs
    app_data = os.getenv('APPDATA') or str(Path.home())
    log_dir = Path(app_data) / "AIStudioConverter" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Настраиваем логирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "converter.log", encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logging.info("Система логирования инициализирована")

def main():
    """
    Главная функция приложения.
    """
    try:
        # Настраиваем логирование
        setup_logging()
        
        # Загружаем настройки
        settings = load_settings()
        logging.info("Настройки загружены")
        
        # Запускаем главное окно
        from app.gui import MainWindow
        window = MainWindow(settings)
        window.show()
        logging.info("Главное окно приложения закрыто")
        
    except Exception as e:
        logging.error(f"Критическая ошибка при запуске приложения: {e}")
        print(f"Ошибка запуска: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
