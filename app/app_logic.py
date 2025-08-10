# -*- coding: utf-8 -*-

import json
import os
import logging
import traceback

logger = logging.getLogger(__name__)

def scan_files(source_dir):
    """
    Сканирует папку и возвращает список всех JSON файлов.
    """
    json_files = []
    try:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.lower().endswith('.json'):
                    json_files.append(os.path.join(root, file))
    except Exception as e:
        logger.error(f"Ошибка при сканировании директории {source_dir}: {str(e)}")
    
    return json_files

def convert_single_file(file_path, dest_dir, settings):
    """
    Конвертирует один JSON файл AI Studio в текстовый формат.
    Возвращает True при успехе, False при ошибке.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Проверяем, что это действительно файл AI Studio
        if not is_ai_studio_file(data):
            logger.warning(f"Файл {file_path} не является файлом AI Studio")
            return False
        
        # Преобразуем в текст
        text_content = convert_to_text(data, settings)
        
        # Создаем имя выходного файла
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_file = os.path.join(dest_dir, f"{base_name}.txt")
        
        # Создаем папку назначения, если её нет
        os.makedirs(dest_dir, exist_ok=True)
        
        # Сохраняем результат
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        logger.info(f"Успешно конвертирован: {file_path} -> {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при конвертации файла {file_path}: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

def is_ai_studio_file(data):
    """
    Проверяет, является ли JSON файл файлом AI Studio.
    """
    # Проверяем наличие ключевых полей AI Studio
    if isinstance(data, dict):
        # Ищем характерные поля AI Studio
        has_contents = 'contents' in data
        has_system_instruction = 'systemInstruction' in data
        has_run_settings = 'runSettings' in data
        
        # Если есть contents с массивом сообщений
        if has_contents and isinstance(data.get('contents'), list):
            return True
        
        # Или если есть systemInstruction или runSettings
        if has_system_instruction or has_run_settings:
            return True
    
    return False

def convert_to_text(data, settings):
    """
    Преобразует JSON данные AI Studio в читаемый текстовый формат.
    """
    result_lines = []
    
    # Добавляем системный промпт, если есть и включен в настройках
    if settings.get('include_system_prompt', True) and 'systemInstruction' in data:
        result_lines.append("=== СИСТЕМНЫЙ ПРОМПТ ===")
        system_instruction = data['systemInstruction']
        if isinstance(system_instruction, dict) and 'parts' in system_instruction:
            for part in system_instruction['parts']:
                if 'text' in part:
                    result_lines.append(part['text'])
        elif isinstance(system_instruction, str):
            result_lines.append(system_instruction)
        result_lines.append("")
    
    # Добавляем настройки запуска, если есть и включены
    if settings.get('include_run_settings', True) and 'runSettings' in data:
        result_lines.append("=== НАСТРОЙКИ МОДЕЛИ ===")
        run_settings = data['runSettings']
        for key, value in run_settings.items():
            result_lines.append(f"{key}: {value}")
        result_lines.append("")
    
    # Обрабатываем основной контент (диалог)
    if 'contents' in data and isinstance(data['contents'], list):
        result_lines.append("=== ДИАЛОГ ===")
        result_lines.append("")
        
        for i, message in enumerate(data['contents']):
            if isinstance(message, dict):
                # Определяем роль
                role = message.get('role', 'unknown')
                role_name = get_role_name(role)
                
                # Проверяем, нужно ли исключать "мысли"
                if settings.get('exclude_thoughts', True):
                    # Проверяем каждую часть сообщения на isThought
                    if 'parts' in message:
                        filtered_parts = []
                        for part in message['parts']:
                            if not part.get('isThought', False):
                                filtered_parts.append(part)
                        if not filtered_parts:
                            continue  # Пропускаем сообщение, если все части - мысли
                        message = message.copy()
                        message['parts'] = filtered_parts
                
                result_lines.append(f"--- {role_name} ---")
                
                # Обрабатываем части сообщения
                if 'parts' in message:
                    for part in message['parts']:
                        if 'text' in part:
                            result_lines.append(part['text'])
                        elif 'inlineData' in part:
                            # Обработка встроенных данных (изображения и т.д.)
                            mime_type = part['inlineData'].get('mimeType', 'unknown')
                            result_lines.append(f"[ВСТРОЕННЫЕ ДАННЫЕ: {mime_type}]")
                
                result_lines.append("")
    
    return "\n".join(result_lines)

def get_role_name(role):
    """
    Переводит роль на русский язык.
    """
    role_map = {
        'user': 'ПОЛЬЗОВАТЕЛЬ',
        'model': 'МОДЕЛЬ',
        'system': 'СИСТЕМА'
    }
    return role_map.get(role, role.upper())

def convert_files(source_dir, dest_dir, settings, progress_queue):
    """
    Главная функция для конвертации файлов. Запускается в отдельном потоке.
    """
    try:
        # Отправляем статус начала работы
        progress_queue.put({"type": "status", "message": "Сканирование файлов..."})
        
        # Сканируем файлы
        json_files = scan_files(source_dir)
        total_files = len(json_files)
        
        if total_files == 0:
            progress_queue.put({"type": "status", "message": "JSON файлы не найдены"})
            progress_queue.put({"type": "done", "total": 0, "errors": 0})
            return
        
        progress_queue.put({"type": "status", "message": f"Найдено {total_files} JSON файлов"})
        
        # Конвертируем файлы
        errors = 0
        for i, file_path in enumerate(json_files):
            current_file = os.path.basename(file_path)
            progress_queue.put({"type": "status", "message": f"Обработка: {current_file}"})
            
            success = convert_single_file(file_path, dest_dir, settings)
            if not success:
                errors += 1
            
            # Отправляем прогресс
            progress_queue.put({"type": "progress", "current": i + 1, "total": total_files})
        
        # Завершение
        progress_queue.put({"type": "status", "message": "Конвертация завершена"})
        progress_queue.put({"type": "done", "total": total_files, "errors": errors})
        
    except Exception as e:
        logger.error(f"Критическая ошибка в convert_files: {str(e)}")
        logger.debug(traceback.format_exc())
        progress_queue.put({"type": "status", "message": f"Критическая ошибка: {str(e)}"})
        progress_queue.put({"type": "done", "total": 0, "errors": 1, "critical_error": str(e)})