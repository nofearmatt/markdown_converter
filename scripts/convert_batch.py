#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пакетная конвертация JSON -> Markdown/HTML через CLI.
Примеры:
  python scripts/convert_batch.py --src ./input --dst ./out --workers 8 --format both --yaml --overwrite
  python scripts/convert_batch.py --src ./input --dst ./out --dry-run
"""
from __future__ import annotations

import os
import sys
import argparse
import queue
import threading
import logging

# Добавляем корень проекта в путь
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.settings import load_settings
from app.app_logic import convert_files


class _DummyQueue:
    def __init__(self):
        self._q = queue.Queue()
        self.seen_warning = False
        self.seen_error = False
        self.seen_success = False
    def put(self, msg):
        t = msg.get('type')
        if t == 'progress':
            val = msg.get('value')
            sys.stdout.write(f"\r[{val:3d}%] {msg.get('message','')}    ")
            sys.stdout.flush()
        else:
            print(f"[{t}] {msg.get('message','')}")
        if t == 'warning':
            self.seen_warning = True
        elif t == 'error':
            self.seen_error = True
        elif t == 'success':
            self.seen_success = True


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch convert AI Studio JSON to Markdown/HTML")
    parser.add_argument('--src', required=True, help='Source directory with JSON files')
    parser.add_argument('--dst', required=True, help='Destination directory')
    parser.add_argument('--format', default='md', choices=['md', 'html', 'both'], help='Export format')
    parser.add_argument('--format-src', dest='source_format', default='auto', choices=['auto','aistudio','chatgpt','claude'], help='Input source format')
    parser.add_argument('--yaml', action='store_true', help='Enable YAML front matter')
    parser.add_argument('--timestamps', action='store_true', help='Include timestamps section')
    parser.add_argument('--system-prompt', dest='system_prompt', action='store_true', help='Include system prompt')
    parser.add_argument('--no-system-prompt', dest='system_prompt', action='store_false', help='Exclude system prompt')
    parser.set_defaults(system_prompt=True)
    parser.add_argument('--run-settings', dest='run_settings', action='store_true', help='Include run settings details')
    parser.add_argument('--no-run-settings', dest='run_settings', action='store_false')
    parser.set_defaults(run_settings=True)
    parser.add_argument('--include-json', action='store_true', help='Append full JSON structure block')
    parser.add_argument('--workers', type=int, default=4, help='Parallel workers (threads)')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing output files')
    parser.add_argument('--no-subfolders', dest='create_subfolders', action='store_false', help='Do not recreate input subfolders in output')
    parser.set_defaults(create_subfolders=True)
    parser.add_argument('--dry-run', action='store_true', help='Do not write files, only simulate')
    parser.add_argument('--rename-extensionless', action='store_true', help='Rename extensionless files in source to .json')
    parser.add_argument('--template', default='', help='Path to Jinja2 template for Markdown')
    parser.add_argument('--html-template', default='', help='Path to Jinja2 template for HTML')
    parser.add_argument('--include', dest='include_globs', default='', help='Semicolon-separated glob patterns to include, relative to src')
    parser.add_argument('--exclude', dest='exclude_globs', default='', help='Semicolon-separated glob patterns to exclude, relative to src')
    parser.add_argument('--zip', dest='zip_output', action='store_true', help='Zip outputs (md/html) created during this run')
    parser.add_argument('--zip-name', dest='zip_name', default='', help='Zip file name without extension')
    parser.add_argument('--pdf', dest='export_pdf', action='store_true', help='Export PDF alongside Markdown/HTML')
    parser.add_argument('--docx', dest='export_docx', action='store_true', help='Export DOCX alongside Markdown/HTML')
    parser.add_argument('--log-file', dest='log_file', default='', help='Log to file')
    parser.add_argument('--log-level', dest='log_level', default='INFO', choices=['DEBUG','INFO','WARNING','ERROR','CRITICAL'], help='Logging level')

    args = parser.parse_args()

    # Логирование
    level = getattr(logging, args.log_level.upper(), logging.INFO)
    if args.log_file:
        logging.basicConfig(filename=args.log_file, level=level, format='%(asctime)s %(levelname)s %(message)s')
    else:
        logging.basicConfig(level=level, format='%(asctime)s %(levelname)s %(message)s')

    src = os.path.abspath(args.src)
    dst = os.path.abspath(args.dst)
    os.makedirs(dst, exist_ok=True)

    settings = load_settings()
    settings.update({
        'source_format': args.source_format,
        'source_dir': src,
        'dest_dir': dst,
        'include_metadata': True,
        'include_timestamps': bool(args.timestamps),
        'include_system_prompt': bool(args.system_prompt),
        'overwrite_existing': bool(args.overwrite),
        'create_subfolders': bool(args.create_subfolders),
        'include_json_structure': bool(args.include_json),
        'add_file_headers': True,
        'include_run_settings': bool(args.run_settings),
        'exclude_thoughts': True,
        'dry_run': bool(args.dry_run),
        'rename_extensionless': bool(args.rename_extensionless),
        'workers': max(1, int(args.workers)),
        'export_format': args.format,
        'template_path': args.template,
        'html_template_path': args.html_template,
        'enable_yaml_front_matter': bool(args.yaml),
        'include_globs': args.include_globs,
        'exclude_globs': args.exclude_globs,
        'zip_output': bool(args.zip_output),
        'zip_name': args.zip_name.strip(),
        'export_pdf': bool(args.export_pdf),
        'export_docx': bool(args.export_docx),
    })

    cancel_event = threading.Event()
    settings['cancel_event'] = cancel_event

    q = _DummyQueue()
    exit_code = 0
    try:
        convert_files(src, dst, settings, q)
        if q.seen_error:
            exit_code = 2
        elif q.seen_warning:
            exit_code = 1
        else:
            exit_code = 0 if q.seen_success else 1
    except KeyboardInterrupt:
        cancel_event.set()
        print("\nОтмена по запросу пользователя...")
        exit_code = 2
    print("\nГотово.")
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())