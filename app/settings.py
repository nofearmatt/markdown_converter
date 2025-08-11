# -*- coding: utf-8 -*-
"""
Модуль для работы с настройками приложения.
Сохраняет и загружает настройки в файл settings.json в папке %APPDATA%
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, Any

def get_settings_file_path() -> str:
    """
    Возвращает путь к файлу настроек в папке %APPDATA%.
    
    Returns:
        str: Полный путь к файлу настроек
    """
    app_data = os.getenv('APPDATA')
    if not app_data:
        # Fallback для случаев, когда APPDATA не установлена
        app_data = os.path.expanduser('~')
    
    # Создаем папку для нашего приложения
    app_folder = os.path.join(app_data, 'AIStudioConverter')
    os.makedirs(app_folder, exist_ok=True)
    
    return os.path.join(app_folder, 'settings.json')

def get_default_settings() -> Dict[str, Any]:
    """
    Возвращает настройки по умолчанию.
    
    Returns:
        Dict[str, Any]: Словарь с настройками по умолчанию
    """
    return {
        # Базовые пути
        "source_dir": "",
        "dest_dir": "",

        # Поведение конвертера / рендеринг
        "include_metadata": True,
        "include_timestamps": False,
        "overwrite_existing": False,
        "create_subfolders": True,
        "include_json_structure": False,
        "add_file_headers": True,

        # Зарезервированные поля для совместимости и будущих функций
        "include_system_prompt": True,
        "include_run_settings": True,
        "exclude_thoughts": True
    }

def load_settings() -> Dict[str, Any]:
    """
    Загружает настройки из файла. Если файл не существует или поврежден,
    возвращает настройки по умолчанию.
    
    Returns:
        Dict[str, Any]: Загруженные настройки
    """
    settings_file = get_settings_file_path()
    
    try:
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)
                
            # Проверяем, что все необходимые ключи присутствуют
            default_settings = get_default_settings()
            for key, default_value in default_settings.items():
                if key not in loaded_settings:
                    loaded_settings[key] = default_value
                    
            return loaded_settings
        else:
            logging.info("Файл настроек не найден, используются настройки по умолчанию")
            return get_default_settings()
            
    except (json.JSONDecodeError, IOError, OSError) as e:
        logging.error(f"Ошибка при загрузке настроек: {str(e)}")
        logging.info("Используются настройки по умолчанию")
        return get_default_settings()

def save_settings(settings: Dict[str, Any]) -> bool:
    """
    Сохраняет настройки в файл.
    
    Args:
        settings: Словарь с настройками для сохранения
        
    Returns:
        bool: True если сохранение прошло успешно, False в противном случае
    """
    try:
        settings_file = get_settings_file_path()
        
        # Создаем временный файл для безопасного сохранения
        temp_file = settings_file + '.tmp'
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        
        # Атомарно заменяем старый файл новым
        if os.path.exists(settings_file):
            os.remove(settings_file)
        os.rename(temp_file, settings_file)
        
        logging.info("Настройки успешно сохранены")
        return True
        
    except (IOError, OSError) as e:
        logging.error(f"Ошибка при сохранении настроек: {str(e)}")
        return False

def reset_settings() -> bool:
    """
    Сбрасывает настройки к значениям по умолчанию.
    
    Returns:
        bool: True если сброс прошел успешно, False в противном случае
    """
    try:
        default_settings = get_default_settings()
        return save_settings(default_settings)
    except Exception as e:
        logging.error(f"Ошибка при сбросе настроек: {str(e)}")
        return False
