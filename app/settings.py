# -*- coding: utf-8 -*-

import json
import os
import logging

logger = logging.getLogger(__name__)

def get_settings_dir():
    """
    Возвращает путь к папке для хранения настроек приложения.
    Использует %APPDATA% на Windows или ~/.config на Linux/macOS.
    """
    if os.name == 'nt':  # Windows
        app_data = os.getenv('APPDATA')
        if app_data:
            return os.path.join(app_data, 'AIStudioConverter')
    
    # Linux/macOS
    home = os.path.expanduser('~')
    return os.path.join(home, '.config', 'AIStudioConverter')

def get_settings_file_path():
    """
    Возвращает полный путь к файлу настроек.
    """
    settings_dir = get_settings_dir()
    return os.path.join(settings_dir, 'settings.json')

def load_settings():
    """
    Загружает настройки из файла. Если файла нет, возвращает настройки по умолчанию.
    """
    default_settings = {
        "source_dir": "",
        "dest_dir": "",
        "include_system_prompt": True,
        "include_run_settings": True,
        "exclude_thoughts": True
    }
    
    settings_file = get_settings_file_path()
    
    try:
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                saved_settings = json.load(f)
            
            # Объединяем сохраненные настройки с настройками по умолчанию
            # Это гарантирует, что у нас есть все необходимые ключи
            for key, value in default_settings.items():
                if key not in saved_settings:
                    saved_settings[key] = value
            
            logger.info(f"Настройки загружены из {settings_file}")
            return saved_settings
        else:
            logger.info("Файл настроек не найден, используются настройки по умолчанию")
            return default_settings
            
    except Exception as e:
        logger.error(f"Ошибка при загрузке настроек из {settings_file}: {str(e)}")
        logger.info("Используются настройки по умолчанию")
        return default_settings

def save_settings(settings):
    """
    Сохраняет настройки в файл.
    """
    settings_file = get_settings_file_path()
    settings_dir = get_settings_dir()
    
    try:
        # Создаем папку для настроек, если её нет
        os.makedirs(settings_dir, exist_ok=True)
        
        # Сохраняем настройки
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Настройки сохранены в {settings_file}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении настроек в {settings_file}: {str(e)}")
        return False

def get_settings_info():
    """
    Возвращает информацию о местоположении файла настроек.
    Полезно для отладки.
    """
    settings_file = get_settings_file_path()
    settings_dir = get_settings_dir()
    
    return {
        "settings_directory": settings_dir,
        "settings_file": settings_file,
        "file_exists": os.path.exists(settings_file),
        "directory_exists": os.path.exists(settings_dir)
    }