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
from typing import Dict, Any, List, Optional, Tuple

import base64
import mimetypes
import threading
import time
import fnmatch
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from jinja2 import Environment, FileSystemLoader
import markdown as md


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
    logging.info("НАЧАЛО КОНВЕРТАЦИИ AI STUDIO В MARKDOWN/HTML")
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
                    # Упрощенная поддержка ссылок на вложения
                    image_url = seg.get('imageUrl') or seg.get('image_url')
                    if isinstance(image_url, str) and image_url:
                        chunks.append(f"![image]({image_url})")
                    file_url = seg.get('fileUrl') or seg.get('file_url')
                    if isinstance(file_url, str) and file_url:
                        chunks.append(f"[attachment]({file_url})")
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


def _guess_extension_from_mime(mime_type: str) -> str:
    ext = mimetypes.guess_extension(mime_type or '') or ''
    if not ext:
        mapping = {
            'image/png': '.png',
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/webp': '.webp',
            'image/gif': '.gif',
            'text/plain': '.txt',
            'application/pdf': '.pdf',
        }
        ext = mapping.get((mime_type or '').lower(), '')
    return ext or ''


def _find_inline_attachments(data: Any) -> List[Tuple[Optional[str], Optional[str], Optional[str]]]:
    """
    Ищет в произвольной структуре словарей/списков элементы с inlineData (data + mimeType)
    и ссылки imageUrl/fileUrl. Возвращает список кортежей (base64_data, mimeType, remote_url).
    """
    found: List[Tuple[Optional[str], Optional[str], Optional[str]]] = []

    def _walk(obj: Any):
        if isinstance(obj, dict):
            inline = obj.get('inlineData') or obj.get('inline_data')
            if isinstance(inline, dict):
                b64 = inline.get('data')
                m = inline.get('mimeType') or inline.get('mime_type')
                if isinstance(b64, str) and isinstance(m, str):
                    found.append((b64, m, None))
            image_url = obj.get('imageUrl') or obj.get('image_url')
            if isinstance(image_url, str):
                found.append((None, None, image_url))
            file_url = obj.get('fileUrl') or obj.get('file_url')
            if isinstance(file_url, str):
                found.append((None, None, file_url))
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(data)
    return found


def _render_markdown_with_template(md_text: str, settings: Dict[str, Any], context: Dict[str, Any]) -> str:
    template_path = settings.get('template_path') or ''
    if template_path and os.path.exists(template_path):
        env = Environment(loader=FileSystemLoader(os.path.dirname(template_path)), autoescape=False)
        template = env.get_template(os.path.basename(template_path))
        return template.render({**context, 'content': md_text})
    return md_text


def _wrap_with_yaml_front_matter(md_text: str, front_matter: Dict[str, Any], enable: bool) -> str:
    if not enable:
        return md_text
    try:
        import yaml  # lazy import
        yaml_text = yaml.safe_dump(front_matter, allow_unicode=True, sort_keys=False).strip()
        return f"---\n{yaml_text}\n---\n\n" + md_text
    except Exception:
        return md_text


def _build_front_matter(data: Dict[str, Any], run_settings: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
    title = settings.get('__source_basename') or data.get('title') or 'AI Studio Конвертация'
    fm: Dict[str, Any] = {
        'title': title,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    model = (run_settings or {}).get('model') or (run_settings or {}).get('modelName')
    if model:
        fm['model'] = model
    return fm


def _render_html_from_markdown(md_text_without_yaml: str, settings: Dict[str, Any], context: Dict[str, Any]) -> str:
    html_body = md.markdown(md_text_without_yaml, extensions=['fenced_code', 'tables'])
    html_template_path = settings.get('html_template_path') or ''
    if html_template_path and os.path.exists(html_template_path):
        env = Environment(loader=FileSystemLoader(os.path.dirname(html_template_path)), autoescape=False)
        template = env.get_template(os.path.basename(html_template_path))
        return template.render({**context, 'content_html': html_body, 'content_markdown': md_text_without_yaml})
    # Fallback простой HTML
    return f"""
<!doctype html>
<html lang=\"ru\">
<head>
<meta charset=\"utf-8\" />
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
<title>{context.get('title', 'Document')}</title>
<style>
body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; line-height: 1.6; max-width: 860px; margin: 24px auto; padding: 0 16px; }}
h1,h2,h3,h4 {{ line-height: 1.25; }}
code, pre {{ background: #0b0f14; color: #e6e6e6; border-radius: 6px; }}
pre {{ padding: 12px; overflow: auto; }}
table {{ border-collapse: collapse; }}
th, td {{ border: 1px solid #ddd; padding: 6px 10px; }}
blockquote {{ border-left: 4px solid #ccc; margin: 0; padding: 0 12px; color: #555; }}
hr {{ border: none; border-top: 1px solid #e0e0e0; margin: 24px 0; }}
</style>
</head>
<body>
{html_body}
</body>
</html>
"""


def convert_single_file(json_file_path: str, dest_dir: str, settings: Dict[str, Any]) -> bool:
    """
    Конвертирует один JSON файл в формат Markdown/HTML.
    
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
        md_content_core = extract_markdown_content(data, settings_with_fallback)

        # Front matter
        run_settings = data.get('run_settings') or data.get('runSettings') or {}
        front_matter = _build_front_matter(data, run_settings, settings_with_fallback)
        md_with_front_matter = _wrap_with_yaml_front_matter(
            md_content_core, front_matter, settings_with_fallback.get('enable_yaml_front_matter', False)
        )

        # Рендер Markdown через шаблон (если задан)
        context = {
            'title': front_matter.get('title'),
            'data': data,
            'settings': settings_with_fallback,
            'run_settings': run_settings,
            'now': datetime.now().isoformat(timespec='seconds')
        }
        md_final = _render_markdown_with_template(md_with_front_matter, settings_with_fallback, context)

        # Подготовка путей
        md_filename = f"{base_name}.md"
        html_filename = f"{base_name}.html"
        final_dest_dir = dest_dir

        # Создаем подпапки если включено
        if settings.get("create_subfolders", True):
            source_dir = settings.get("source_dir", "")
            if source_dir:
                rel_path = os.path.relpath(os.path.dirname(json_file_path), source_dir)
                if rel_path != ".":
                    final_dest_dir = os.path.join(dest_dir, rel_path)
                    os.makedirs(final_dest_dir, exist_ok=True)

        # Вложения (inline/base64 и ссылки) -> сохраняем файлы и добавим раздел в конец MD
        assets_dir = os.path.join(final_dest_dir, f"{base_name}_assets")
        attachments = _find_inline_attachments(data)
        saved_attachments: List[str] = []
        if attachments:
            os.makedirs(assets_dir, exist_ok=True)
            counter = 1
            for b64_data, mime_type, remote_url in attachments:
                if remote_url:
                    saved_attachments.append(remote_url)
                    continue
                if b64_data and mime_type:
                    try:
                        raw = base64.b64decode(b64_data)
                        ext = _guess_extension_from_mime(mime_type) or f"_{counter}"
                        file_name = f"att_{counter}{ext}"
                        out_path = os.path.join(assets_dir, file_name)
                        if not settings.get('dry_run', False):
                            with open(out_path, 'wb') as wf:
                                wf.write(raw)
                        saved_attachments.append(os.path.join(f"{base_name}_assets", file_name))
                        counter += 1
                    except Exception as e:
                        logging.warning(f"Не удалось сохранить вложение: {e}")

        if saved_attachments:
            md_final += "\n\n## 📎 Вложения\n"
            for link in saved_attachments:
                if link.startswith('http'):
                    md_final += f"- [attachment]({link})\n"
                else:
                    md_final += f"- ![attachment]({link})\n"

        # Определяем форматы экспорта
        export_format = (settings.get('export_format') or 'md').lower()
        write_md = export_format in ('md', 'both')
        write_html = export_format in ('html', 'both')

        # Полные пути
        md_output_path = os.path.join(final_dest_dir, md_filename)
        html_output_path = os.path.join(final_dest_dir, html_filename)

        # DRY-RUN
        if settings.get('dry_run', False):
            logging.info(f"[DRY-RUN] {json_file_path} -> {md_output_path if write_md else ''} {html_output_path if write_html else ''}")
            return True

        # Проверяем существование файла
        if write_md and os.path.exists(md_output_path) and not settings.get("overwrite_existing", False):
            logging.warning(f"Файл {md_output_path} уже существует. Пропускаем без ошибки.")
            write_md = False
        if write_html and os.path.exists(html_output_path) and not settings.get("overwrite_existing", False):
            logging.warning(f"Файл {html_output_path} уже существует. Пропускаем без ошибки.")
            write_html = False

        # Записываем MD
        if write_md:
            with open(md_output_path, 'w', encoding='utf-8') as f:
                f.write(md_final)

        # Готовим HTML из Markdown без YAML префикса (если он был)
        if write_html:
            # Уберем YAML префикс, если есть
            if md_final.startswith('---\n'):
                try:
                    end_idx = md_final.index('\n---\n', 4)
                    md_for_html = md_final[end_idx + 5 :]
                except ValueError:
                    md_for_html = md_final
            else:
                md_for_html = md_final

            html_text = _render_html_from_markdown(md_for_html, settings_with_fallback, context)
            with open(html_output_path, 'w', encoding='utf-8') as f:
                f.write(html_text)
        
        logging.info(f"Успешно конвертирован: {json_file_path} -> {final_dest_dir}")
        return True
        
    except json.JSONDecodeError as e:
        logging.error(f"Ошибка парсинга JSON в файле {json_file_path}: {e}")
        return False
    except Exception as e:
        logging.error(f"Ошибка при конвертации файла {json_file_path}: {e}")
        return False


def render_markdown_preview(json_file_path: str, settings: Dict[str, Any]) -> str:
    """
    Генерирует Markdown (с учетом шаблонов и YAML FM) для предпросмотра, без записи на диск.
    """
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    json_filename = os.path.basename(json_file_path)
    base_name = os.path.splitext(json_filename)[0]
    settings_with_fallback = dict(settings)
    settings_with_fallback['__source_basename'] = base_name

    md_content_core = extract_markdown_content(data, settings_with_fallback)
    run_settings = data.get('run_settings') or data.get('runSettings') or {}
    front_matter = _build_front_matter(data, run_settings, settings_with_fallback)
    md_with_front_matter = _wrap_with_yaml_front_matter(
        md_content_core, front_matter, settings_with_fallback.get('enable_yaml_front_matter', False)
    )
    context = {
        'title': front_matter.get('title'),
        'data': data,
        'settings': settings_with_fallback,
        'run_settings': run_settings,
        'now': datetime.now().isoformat(timespec='seconds')
    }
    md_final = _render_markdown_with_template(md_with_front_matter, settings_with_fallback, context)

    # Добавим список вложений (без сохранения файлов)
    attachments = _find_inline_attachments(data)
    if attachments:
        md_final += "\n\n## 📎 Вложения\n"
        counter = 1
        for b64_data, mime_type, remote_url in attachments:
            if remote_url:
                md_final += f"- [attachment]({remote_url})\n"
            else:
                label = f"inline_{counter}.{_guess_extension_from_mime(mime_type).lstrip('.')}" if mime_type else f"inline_{counter}"
                md_final += f"- {label}\n"
                counter += 1
    return md_final


def convert_files(source_dir: str, dest_dir: str, settings: Dict[str, Any], progress_queue) -> None:
    """
    Основная функция конвертации файлов AI Studio в Markdown/HTML.
    
    Args:
        source_dir: Папка с исходными JSON файлами
        dest_dir: Папка для сохранения результатов
        settings: Настройки конвертации
        progress_queue: Очередь для отправки прогресса в GUI/CLI
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
        
        # По флагу: добавим .json ко всем файлам без расширения
        try:
            if settings.get('rename_extensionless', False):
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
        
        # Фильтрация include/exclude по glob
        include_globs: List[str] = []
        exclude_globs: List[str] = []
        inc = settings.get('include_globs') or settings.get('include_glob')
        exc = settings.get('exclude_globs') or settings.get('exclude_glob')
        if isinstance(inc, str) and inc.strip():
            include_globs = [p.strip() for p in inc.split(';') if p.strip()]
        elif isinstance(inc, list):
            include_globs = [str(p) for p in inc]
        if isinstance(exc, str) and exc.strip():
            exclude_globs = [p.strip() for p in exc.split(';') if p.strip()]
        elif isinstance(exc, list):
            exclude_globs = [str(p) for p in exc]

        if include_globs or exclude_globs:
            filtered: List[str] = []
            for p in json_files:
                rel = os.path.relpath(p, source_dir)
                keep = True
                if include_globs:
                    keep = any(fnmatch.fnmatch(rel, pat) for pat in include_globs)
                if keep and exclude_globs:
                    if any(fnmatch.fnmatch(rel, pat) for pat in exclude_globs):
                        keep = False
                if keep:
                    filtered.append(p)
            json_files = filtered

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
        
        # Конвертируем файлы (возможна параллельная обработка)
        successful_conversions = 0
        failed_conversions = 0
        total = len(json_files)
        completed = 0
        workers = max(1, int(settings.get('workers', 1)))

        # Отмена и ETA
        cancel_event: Optional[threading.Event] = settings.get('cancel_event') if isinstance(settings.get('cancel_event'), threading.Event) else None
        start_ts = time.time()
        last_progress_emit = 0.0

        def _convert_wrapper(path: str) -> Tuple[str, bool]:
            ok = convert_single_file(path, dest_dir, settings)
            return path, ok

        if workers == 1:
            for i, json_file in enumerate(json_files):
                if cancel_event and cancel_event.is_set():
                    break
                progress_queue.put({
                    "type": "progress",
                    "value": int((i / total) * 100),
                    "message": f"Конвертация файла {i+1} из {total}: {os.path.basename(json_file)}"
                })
                if convert_single_file(json_file, dest_dir, settings):
                    successful_conversions += 1
                else:
                    failed_conversions += 1
                completed += 1
                # ETA
                dt = time.time() - start_ts
                if completed > 0 and dt > 0 and (time.time() - last_progress_emit) > 0.5:
                    avg = dt / completed
                    remain = max(0, int((total - completed) * avg))
                    progress_queue.put({
                        "type": "info",
                        "message": f"ETA ~ {remain}s"
                    })
                    last_progress_emit = time.time()
        else:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                future_to_path = {executor.submit(_convert_wrapper, p): p for p in json_files}
                for fut in as_completed(future_to_path):
                    if cancel_event and cancel_event.is_set():
                        break
                    path, ok = fut.result()
                    completed += 1
                    if ok:
                        successful_conversions += 1
                    else:
                        failed_conversions += 1
                    progress_queue.put({
                        "type": "progress",
                        "value": int((completed / total) * 100),
                        "message": f"Готово {completed}/{total}: {os.path.basename(path)}"
                    })
                    # ETA
                    dt = time.time() - start_ts
                    if completed > 0 and dt > 0 and (time.time() - last_progress_emit) > 0.5:
                        avg = dt / completed
                        remain = max(0, int((total - completed) * avg))
                        progress_queue.put({
                            "type": "info",
                            "message": f"ETA ~ {remain}s"
                        })
                        last_progress_emit = time.time()
 
        # Отправляем финальный прогресс
        progress_queue.put({
            "type": "progress",
            "value": 100,
            "message": "Конвертация завершена"
        })
        
        # Логируем результаты
        logging.info(f"Конвертация завершена. Успешно: {successful_conversions}, Ошибок: {failed_conversions}")
        
        # Упаковка в ZIP, если включено
        if settings.get('zip_output'):
            zip_name = settings.get('zip_name') or f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            zip_path = os.path.join(dest_dir, f"{zip_name}.zip")
            created_after = start_ts - 1  # небольшая фора
            exts = {'.md', '.html'}
            try:
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for root, _, files in os.walk(dest_dir):
                        for f in files:
                            if os.path.splitext(f)[1].lower() in exts:
                                full = os.path.join(root, f)
                                if os.path.getmtime(full) >= created_after:
                                    arcname = os.path.relpath(full, dest_dir)
                                    zf.write(full, arcname)
                progress_queue.put({"type": "info", "message": f"ZIP создан: {zip_path}"})
            except Exception as e:
                progress_queue.put({"type": "warning", "message": f"Не удалось создать ZIP: {e}"})

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
