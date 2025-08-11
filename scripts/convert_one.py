#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита для конвертации одного JSON-файла в Markdown с «богатым» рендером.

Использование:
  python scripts/convert_one.py "ВходнойФайл.json" "папка_вывода" [--overwrite]
"""

import os
import sys
import argparse

# Добавляем папку app в путь для импорта
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.settings import load_settings
from app.app_logic import convert_single_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert single JSON to Markdown (rich style)")
    parser.add_argument('input_path', help='Путь к входному JSON-файлу')
    parser.add_argument('output_dir', help='Папка для сохранения .md')
    parser.add_argument('--overwrite', action='store_true', help='Перезаписывать существующий .md')
    args = parser.parse_args()

    input_path = args.input_path
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    settings = load_settings()
    # Включаем «богатый» рендер и нужные флаги
    settings.update({
        'include_metadata': True,
        'include_timestamps': True,
        'include_system_prompt': True,
        'include_run_settings': True,
        'exclude_thoughts': True,
        'add_file_headers': True,
        'include_json_structure': False,
        'create_subfolders': False,
        'overwrite_existing': bool(args.overwrite),
        'source_dir': os.getcwd(),
        'dest_dir': output_dir,
    })

    ok = convert_single_file(input_path, output_dir, settings)
    out_name = os.path.splitext(os.path.basename(input_path))[0] + '.md'
    out_path = os.path.join(output_dir, out_name)

    print(f"OK: {ok}")
    print(f"Output: {out_path}")
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())


