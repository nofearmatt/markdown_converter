# План релизов (Draft)

## Iteration 1 (2 недели)
- Parser & Normalization (AI Studio, ChatGPT, Claude)
- Детектор формата
- Тестовые фикстуры и pytest
- CLI: расширенные флаги (format-src, logs)

Deliverables:
- Библиотека нормализации + тесты (>=70%)
- CLI конвертация для 3 источников

## Iteration 2 (2 недели)
- Экспорт PDF/DOCX (опциональный)
- Индекс/оглавление (index.md/html)
- Пресеты, «Недавние проекты»
- HTML preview в GUI

Deliverables:
- PDF/DOCX экспорт, базовые шаблоны
- Улучшенный GUI (preview, пресеты)

## Iteration 3 (1-2 недели)
- Watcher стабильность, дебаунс
- Perf улучшения (кэш шаблонов, процессный пул)
- CI/CD (линтеры, тесты, сборка .exe)
- Документация и примеры шаблонов

Deliverables:
- Сборки для Windows/macOS/Linux (где возможно)
- Полная документация и набор примеров

Owners:
- Parser & Normalization: TBD
- Export & Templates: TBD
- GUI/UX: TBD
- DevOps/CI: TBD