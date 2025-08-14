# AI Studio Converter

Конвертер JSON файлов AI Studio в формат Markdown/HTML с современным графическим интерфейсом и CLI.

## Описание

AI Studio Converter — десктопное приложение для Windows/macOS/Linux, которое конвертирует JSON из AI Studio в читаемый Markdown и HTML. Современный GUI на CustomTkinter, многопоточность, шаблоны Jinja2, YAML front matter, режим наблюдения за папкой.

## Возможности

- 🎯 Конвертация JSON → Markdown/HTML
- 🖥️ Современный GUI (CustomTkinter)
- ⚡ Многопоточность (настройка числа потоков)
- 🧩 Шаблоны (Jinja2) для Markdown/HTML
- 🧾 YAML Front Matter (для блогов/документации)
- 💾 Сохранение настроек (кроссплатформенно)
- 🧪 Dry-run (пробный запуск)
- 👁️ Watcher: автоконвертация новых JSON
- 📊 Прогресс и лог
- 🛡️ Безопасные опции: не менять исходники без флага, фильтр мыслей

## Требования

- Python 3.10 или выше
- Windows 10/11, macOS, Linux
- 100 МБ свободного места на диске

## Установка

### Из исходников

```bash
pip install -r requirements.txt --break-system-packages  # если система управляет Python
# или используйте venv и обычный pip install -r requirements.txt
```

### Сборка .exe (Windows)

```bash
pyinstaller --noconfirm --windowed --onefile --name MDGenerator main.py
```

## Использование GUI

1. Запустите `python main.py`
2. Выберите папку с JSON и папку назначения
3. Настройте флаги (формат, шаблоны, YAML, потоки, dry-run и т.д.)
4. Нажмите «Начать конвертацию»
5. Опционально — «Запустить наблюдение» для автоконвертации

## CLI

Пакетная конвертация:

```bash
python scripts/convert_batch.py --src ./input --dst ./out --workers 8 --format both --yaml --overwrite
```

Dry-run:

```bash
python scripts/convert_batch.py --src ./input --dst ./out --dry-run
```

Основные флаги:
- `--format md|html|both` — формат вывода
- `--yaml` — включить YAML front matter
- `--timestamps` — включить секцию временных меток
- `--run-settings/--no-run-settings` — секция Run Settings
- `--template`, `--html-template` — пути к шаблонам Jinja2
- `--workers N` — число потоков
- `--overwrite` — перезаписывать существующие
- `--no-subfolders` — не повторять структуру подпапок
- `--rename-extensionless` — переименовывать файлы без расширения в .json (в source)

## Технические детали

### Архитектура

- GUI поток (CustomTkinter) + рабочие потоки (ThreadPoolExecutor)
- Очередь сообщений прогресса между потоками
- Наблюдатель директорий (watchdog)

### Настройки

- Сохраняются в кроссплатформенной папке пользователя (platformdirs)
- Ключевые опции: export_format, workers, dry_run, enable_yaml_front_matter, шаблоны

## Разработка

- Логика конвертации: `app/app_logic.py`
- GUI: `app/gui.py`
- Watcher: `app/watcher.py`
- CLI: `scripts/convert_batch.py`, `scripts/convert_one.py`

## Лицензия

MIT — см. `LICENSE`.
