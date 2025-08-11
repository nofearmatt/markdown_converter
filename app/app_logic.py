# -*- coding: utf-8 -*-
"""
Модуль логики конвертации файлов AI Studio.
Отвечает за сканирование папок, обработку JSON файлов и конвертацию в формат .md
"""

import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

def ensure_destination_directory(dest_dir: str) -> bool:
    """
    Создает папку назначения, если она не существует.
    
    Args:
        dest_dir: Путь к папке назначения
        
    Returns:
        bool: True если папка создана или уже существует, False в случае ошибки
    """
    try:
        os.makedirs(dest_dir, exist_ok=True)
        return True
    except Exception as e:
        logging.error(f"Ошибка при создании папки назначения {dest_dir}: {e}")
        return False

def ensure_json_extension_for_extensionless_files(root_dir: str) -> int:
    """
    Рекурсивно добавляет расширение .json всем файлам без расширения в папке.
    Возвращает количество переименованных файлов. При коллизии добавляет суффикс _jsonN.
    """
    renamed_count = 0
    for dirpath, _, filenames in os.walk(root_dir):
        for name in filenames:
            base, ext = os.path.splitext(name)
            if ext:
                continue
            src_path = os.path.join(dirpath, name)
            candidate = f"{name}.json"
            dst_path = os.path.join(dirpath, candidate)
            if os.path.exists(dst_path):
                i = 1
                while True:
                    alt = os.path.join(dirpath, f"{name}_json{i}.json")
                    if not os.path.exists(alt):
                        dst_path = alt
                        break
                    i += 1
            try:
                os.rename(src_path, dst_path)
                renamed_count += 1
            except Exception:
                continue
    return renamed_count

def validate_settings(settings: Dict[str, Any]) -> bool:
    """
    Проверяет корректность настроек конвертации.
    
    Args:
        settings: Словарь с настройками
        
    Returns:
        bool: True если настройки корректны, False в противном случае
    """
    required_keys = ['source_dir', 'dest_dir']
    for key in required_keys:
        if key not in settings:
            logging.error(f"Отсутствует обязательный параметр: {key}")
            return False
    
    # Проверяем существование исходной папки
    if not os.path.exists(settings['source_dir']):
        logging.error(f"Исходная папка не существует: {settings['source_dir']}")
        return False
    
    return True

def log_conversion_process(source_dir: str, dest_dir: str, settings: Dict[str, Any]) -> None:
    """
    Логирует информацию о процессе конвертации.
    
    Args:
        source_dir: Исходная папка
        dest_dir: Папка назначения
        settings: Настройки конвертации
    """
    logging.info("=" * 60)
    logging.info("НАЧАЛО КОНВЕРТАЦИИ AI STUDIO В MARKDOWN")
    logging.info("=" * 60)
    logging.info(f"Исходная папка: {source_dir}")
    logging.info(f"Папка назначения: {dest_dir}")
    logging.info(f"Настройки: {json.dumps(settings, indent=2, ensure_ascii=False)}")
    logging.info("=" * 60)

def extract_markdown_content(data: Dict[str, Any], settings: Dict[str, Any]) -> str:
    """
    Извлекает содержимое для Markdown из JSON данных согласно настройкам.
    Реализует «богатый» стиль оформления с секциями: метаданные, system prompt,
    run settings и красиво оформленные сообщения.
    """

    def get_nested(obj: Dict[str, Any], path: str, default=None):
        current = obj
        for part in path.split('.'):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current

    def first_of(paths: List[str], default=None):
        for p in paths:
            val = get_nested(data, p, None)
            if val is not None:
                return val
        return default

    def coalesce_title() -> str:
        candidates = [
            get_nested(data, 'conversation.title'),
            data.get('conversationTitle'),
            get_nested(data, 'chat.title'),
            get_nested(data, 'thread.title'),
            get_nested(data, 'session.title'),
            get_nested(data, 'metadata.title'),
            data.get('title'),
            data.get('documentTitle'),
            data.get('name'),
        ]
        for t in candidates:
            if isinstance(t, str) and t.strip():
                return t.strip()
        # Фолбэк: имя исходного файла без расширения, если доступно
        fallback = settings.get('__source_basename')
        if isinstance(fallback, str) and fallback.strip():
            return fallback.strip()
        return 'AI Studio Конвертация'

    def normalize_model(run_settings: Dict[str, Any]) -> str:
        if not isinstance(run_settings, dict):
            return ""
        model = run_settings.get('model') or run_settings.get('modelName') or ""
        return str(model)

    def format_run_settings(run_settings: Dict[str, Any]) -> List[str]:
        if not isinstance(run_settings, dict):
            return []
        lines = []
        # Ключевые числовые параметры
        if run_settings.get('temperature') is not None:
            lines.append(f"- temperature: {run_settings.get('temperature')}")
        if run_settings.get('topP') is not None or run_settings.get('topK') is not None:
            lines.append(f"- topP/topK: {run_settings.get('topP', '-')}/{run_settings.get('topK', '-')}")
        if run_settings.get('maxOutputTokens') is not None:
            lines.append(f"- maxOutputTokens: {run_settings.get('maxOutputTokens')}")

        # Флаги
        for flag in [
            'enableCodeExecution',
            'enableSearchAsATool',
            'enableBrowseAsATool',
            'enableAutoFunctionResponse'
        ]:
            if flag in run_settings:
                value = run_settings.get(flag)
                lines.append(f"- {flag}: {'✅' if value else '❌'}")

        # Safety
        safety = run_settings.get('safetySettings')
        if isinstance(safety, list) and safety:
            # Краткая сводка
            all_none = all(isinstance(s, dict) and s.get('threshold') == 'BLOCK_NONE' for s in safety)
            if all_none:
                lines.append("- safety: BLOCK_NONE (все категории)")
            else:
                lines.append("- safety: custom")
        return lines

    def role_label(role: str) -> str:
        r = (role or '').lower()
        if r in ('assistant', 'model', 'ai'):
            return '🤖 Ассистент'
        if r in ('user', 'human'):
            return '🧑‍💻 Пользователь'
        if r == 'system':
            return '🛠️ Система'
        return role.title() if role else 'Сообщение'

    def _join_parts(parts_value) -> str:
        if isinstance(parts_value, list):
            chunks: List[str] = []
            for seg in parts_value:
                if isinstance(seg, dict):
                    # Пропускаем мысли в частях
                    if settings.get('exclude_thoughts', True) and seg.get('thought'):
                        continue
                    txt = seg.get('text')
                    if isinstance(txt, str) and txt:
                        chunks.append(txt)
                elif isinstance(seg, str):
                    chunks.append(seg)
            return "\n".join(chunks).strip()
        elif isinstance(parts_value, str):
            return parts_value
        return ''

    def collect_messages() -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = []
        # 1) Явный массив messages
        explicit = data.get('messages')
        if isinstance(explicit, list):
            for item in explicit:
                if not isinstance(item, dict):
                    continue
                text = item.get('content') or item.get('text')
                if isinstance(text, list):
                    text = _join_parts(text)
                if not text:
                    continue
                messages.append({
                    'role': item.get('role'),
                    'content': text,
                    'timestamp': item.get('timestamp') or item.get('time')
                })

        # 2) chunkedPrompt.chunks
        if not messages:
            chunks = first_of(['chunkedPrompt.chunks'], [])
            if isinstance(chunks, list):
                for ch in chunks:
                    if not isinstance(ch, dict):
                        continue
                    if settings.get('exclude_thoughts', True) and ch.get('isThought'):
                        continue
                    text_val = ch.get('text') or _join_parts(ch.get('parts'))
                    if not text_val:
                        continue
                    messages.append({
                        'role': ch.get('role') or 'model',
                        'content': text_val,
                        'timestamp': ch.get('timestamp') or ch.get('time')
                    })

        return messages

    md_lines: List[str] = []

    # Заголовок
    if settings.get('add_file_headers', True):
        md_lines.append(f"# 🧠 {coalesce_title()}\n")

    # Метаданные и run settings
    include_metadata = settings.get('include_metadata', True)
    run_settings = first_of(['run_settings', 'runSettings'], {}) or {}

    if include_metadata:
        md_lines.append('## 📋 Метаданные')
        model_name = normalize_model(run_settings)
        if model_name:
            md_lines.append(f"- **Модель**: {model_name}")
        if run_settings.get('temperature') is not None:
            md_lines.append(f"- **Температура**: {run_settings.get('temperature')}")
        if run_settings.get('topP') is not None or run_settings.get('topK') is not None:
            md_lines.append(f"- **topP / topK**: {run_settings.get('topP', '-')}/{run_settings.get('topK', '-')}")
        if run_settings.get('maxOutputTokens') is not None:
            md_lines.append(f"- **Макс. токенов**: {run_settings.get('maxOutputTokens')}")
        md_lines.append('')

    # System prompt (если есть и включено)
    if settings.get('include_system_prompt', True):
        sys_prompt = first_of(['system_prompt', 'systemInstruction.text'], None)
        if isinstance(sys_prompt, str) and sys_prompt.strip():
            md_lines.append('## 🛠️ System Prompt')
            md_lines.append('> ' + sys_prompt.replace('\n', '\n> '))
            md_lines.append('')

    # Run settings (подробные флаги)
    if settings.get('include_run_settings', True) and isinstance(run_settings, dict) and run_settings:
        md_lines.append('## ⚙️ Run Settings')
        md_lines.extend(format_run_settings(run_settings))
        md_lines.append('')

    # Сообщения
    messages = collect_messages()
    if messages:
        for idx, msg in enumerate(messages, start=1):
            label = role_label(msg.get('role'))
            ts = msg.get('timestamp')
            if ts and settings.get('include_timestamps', True):
                md_lines.append(f"## [{ts}] {label}")
            else:
                md_lines.append(f"## {label}")
            md_lines.append(msg.get('content', ''))
            if idx < len(messages):
                md_lines.append('\n---\n')
        md_lines.append('')

    # Временные метки конвертации (техн.)
    if settings.get('include_timestamps', True):
        md_lines.append('## ⏰ Временные метки')
        md_lines.append(f"- **Время конвертации**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md_lines.append('')
    
    # JSON структура (если включена)
    if settings.get('include_json_structure', False):
        md_lines.append('## 🔍 JSON Структура')
        md_lines.append('```json')
        md_lines.append(json.dumps(data, indent=2, ensure_ascii=False))
        md_lines.append('```')
    
    return "\n".join(md_lines)

def convert_single_file(json_file_path: str, dest_dir: str, settings: Dict[str, Any]) -> bool:
    """
    Конвертирует один JSON файл в формат Markdown.
    
    Args:
        json_file_path: Путь к исходному JSON файлу
        dest_dir: Папка для сохранения результата
        settings: Настройки конвертации
        
    Returns:
        bool: True если конвертация прошла успешно, False в противном случае
    """
    try:
        # Читаем JSON файл
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Подготовим имя файла для фолбэка заголовка
        json_filename = os.path.basename(json_file_path)
        base_name = os.path.splitext(json_filename)[0]
        settings_with_fallback = dict(settings)
        settings_with_fallback['__source_basename'] = base_name

        # Извлекаем данные согласно настройкам
        md_content = extract_markdown_content(data, settings_with_fallback)
        
        if not md_content:
            logging.warning(f"Не удалось извлечь содержимое из файла {json_file_path}")
            return False
        
        # Определяем имя выходного файла
        # json_filename и base_name уже рассчитаны выше
        md_filename = f"{base_name}.md"
        
        # Определяем папку назначения
        final_dest_dir = dest_dir
        
        # Создаем подпапки если включено
        if settings.get("create_subfolders", True):
            # Получаем относительный путь от исходной папки
            source_dir = settings.get("source_dir", "")
            if source_dir:
                rel_path = os.path.relpath(os.path.dirname(json_file_path), source_dir)
                if rel_path != ".":
                    final_dest_dir = os.path.join(dest_dir, rel_path)
                    # Создаем подпапку если она не существует
                    os.makedirs(final_dest_dir, exist_ok=True)
        
        # Полный путь к выходному файлу
        output_path = os.path.join(final_dest_dir, md_filename)
        
        # Проверяем существование файла
        if os.path.exists(output_path) and not settings.get("overwrite_existing", False):
            # Пропуск существующего файла не считается ошибкой
            logging.warning(f"Файл {output_path} уже существует. Пропускаем без ошибки.")
            return True
        
        # Записываем результат
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logging.info(f"Успешно конвертирован: {json_file_path} -> {output_path}")
        return True
        
    except json.JSONDecodeError as e:
        logging.error(f"Ошибка парсинга JSON в файле {json_file_path}: {e}")
        return False
    except Exception as e:
        logging.error(f"Ошибка при конвертации файла {json_file_path}: {e}")
        return False

def convert_files(source_dir: str, dest_dir: str, settings: Dict[str, Any], progress_queue) -> None:
    """
    Основная функция конвертации файлов AI Studio в Markdown.
    
    Args:
        source_dir: Папка с исходными JSON файлами
        dest_dir: Папка для сохранения результатов
        settings: Настройки конвертации
        progress_queue: Очередь для отправки прогресса в GUI
    """
    try:
        # Логируем начало процесса
        log_conversion_process(source_dir, dest_dir, settings)
        
        # Валидируем настройки
        if not validate_settings(settings):
            progress_queue.put({
                "type": "error",
                "message": "Некорректные настройки конвертации. Проверьте параметры source_dir и dest_dir."
            })
            return
        
        # Проверяем и создаем папку назначения
        if not ensure_destination_directory(dest_dir):
            progress_queue.put({
                "type": "error",
                "message": f"Не удалось создать папку назначения: {dest_dir}"
            })
            return
        
        # Сначала добавим .json ко всем файлам без расширения
        try:
            renamed = ensure_json_extension_for_extensionless_files(source_dir)
            if renamed:
                logging.info(f"Переименовано файлов без расширения: {renamed}")
        except Exception:
            pass

        # Сканируем исходную папку: только .json
        json_files: List[str] = []
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.lower().endswith('.json'):
                    json_files.append(os.path.join(root, file))
        
        if not json_files:
            progress_queue.put({
                "type": "info",
                "message": f"В папке {source_dir} не найдено подходящих JSON-файлов"
            })
            return
        
        logging.info(f"Найдено {len(json_files)} JSON файлов для конвертации")
        progress_queue.put({
            "type": "info",
            "message": f"Найдено {len(json_files)} JSON файлов для конвертации"
        })
        
        # Конвертируем файлы
        successful_conversions = 0
        failed_conversions = 0
        
        for i, json_file in enumerate(json_files):
            # Отправляем прогресс
            progress = int((i / len(json_files)) * 100)
            progress_queue.put({
                "type": "progress",
                "value": progress,
                "message": f"Конвертация файла {i+1} из {len(json_files)}: {os.path.basename(json_file)}"
            })
            
            # Конвертируем файл
            if convert_single_file(json_file, dest_dir, settings):
                successful_conversions += 1
            else:
                failed_conversions += 1
        
        # Отправляем финальный прогресс
        progress_queue.put({
            "type": "progress",
            "value": 100,
            "message": "Конвертация завершена"
        })
        
        # Логируем результаты
        logging.info(f"Конвертация завершена. Успешно: {successful_conversions}, Ошибок: {failed_conversions}")
        
        # Отправляем финальное сообщение
        if failed_conversions == 0:
            progress_queue.put({
                "type": "success",
                "message": f"Конвертация завершена успешно! Обработано файлов: {successful_conversions}"
            })
        else:
            progress_queue.put({
                "type": "warning",
                "message": f"Конвертация завершена с ошибками. Успешно: {successful_conversions}, Ошибок: {failed_conversions}"
            })
            
    except Exception as e:
        error_msg = f"Критическая ошибка при конвертации: {e}"
        logging.error(error_msg)
        progress_queue.put({
            "type": "error",
            "message": error_msg
        })
