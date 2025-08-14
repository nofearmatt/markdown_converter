# Архитектура

## Модули
- `app/app_logic.py` — конвертация, шаблоны, экспорт, параллельная обработка
- `app/gui.py` — GUI на CustomTkinter, предпросмотр, watcher-контролы
- `app/watcher.py` — наблюдение за директорией (watchdog)
- `app/settings.py` — хранение настроек (platformdirs)
- `scripts/convert_batch.py` — CLI пакетной конвертации
- `scripts/convert_one.py` — конвертация одного файла

## Потоки и очереди
- GUI в главном потоке tkinter
- Рабочие потоки (ThreadPoolExecutor) для файлов
- Очередь сообщений (progress_queue) для статусов/прогресса

## Поток данных
1) Источник: JSON (AI Studio/др.)
2) Нормализация (будет вынесена в адаптеры)
3) Рендер Markdown (Jinja2 + YAML FM)
4) Необязательный HTML/PDF/DOCX
5) Запись в `dest_dir` (с подпапками)
6) Опционально ZIP

## Точки расширения
- Адаптеры источников: `adapters/*.py` (планируется)
- Шаблоны тем: `templates/*`
- Экспортеры: `exporters/pdf.py`, `exporters/docx.py` (планируется)

## Ошибки и отмена
- Исключения логируются и агрегируются
- Отмена через `cancel_event` в настройках (GUI/CLI)

## Производительность
- Потоки по I/O; при CPU-bound — планируется пул процессов
- Кэш Jinja2 — планируется