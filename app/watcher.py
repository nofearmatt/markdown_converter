# -*- coding: utf-8 -*-
"""
Наблюдение за директорией и автоматическая конвертация новых/измененных JSON файлов.
"""
from __future__ import annotations

import os
import queue
import threading
import time
from typing import Dict, Any

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from app.app_logic import convert_single_file


class _JsonEventHandler(FileSystemEventHandler):
    def __init__(self, source_dir: str, dest_dir: str, settings: Dict[str, Any], progress_queue):
        super().__init__()
        self.source_dir = source_dir
        self.dest_dir = dest_dir
        self.settings = settings
        self.progress_queue = progress_queue
        self._lock = threading.Lock()
        self._last_seen: Dict[str, float] = {}
        self._debounce_sec = 0.5

    def on_any_event(self, event: FileSystemEvent):
        if event.is_directory:
            return
        path = event.src_path
        if not str(path).lower().endswith('.json'):
            return
        now = time.time()
        last = self._last_seen.get(path, 0.0)
        if now - last < self._debounce_sec:
            return
        self._last_seen[path] = now
        with self._lock:
            try:
                ok = convert_single_file(path, self.dest_dir, self.settings)
                msg = f"Автоконвертация: {'успех' if ok else 'ошибка'} — {os.path.basename(path)}"
                self.progress_queue.put({"type": "info", "message": msg})
            except Exception as e:
                self.progress_queue.put({"type": "error", "message": f"Ошибка watcher: {e}"})


class DirectoryWatcher:
    def __init__(self, source_dir: str, dest_dir: str, settings: Dict[str, Any], progress_queue):
        self.source_dir = source_dir
        self.dest_dir = dest_dir
        self.settings = settings
        self.progress_queue = progress_queue
        self._observer: Observer | None = None

    def start(self):
        if self._observer is not None:
            return
        handler = _JsonEventHandler(self.source_dir, self.dest_dir, self.settings, self.progress_queue)
        observer = Observer()
        observer.schedule(handler, self.source_dir, recursive=True)
        observer.start()
        self._observer = observer
        self.progress_queue.put({"type": "info", "message": "Watcher запущен"})

    def stop(self):
        if self._observer is None:
            return
        self._observer.stop()
        self._observer.join(timeout=3)
        self._observer = None
        self.progress_queue.put({"type": "info", "message": "Watcher остановлен"})