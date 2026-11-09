"""Çeviri geçmişi. Varsayılan olarak KAPALI. Açıksa kayıtlar yalnızca bu bilgisayarda
``%APPDATA%\\AITranslator\\history.jsonl`` dosyasında tutulur."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from .paths import history_path

MAX_ENTRIES = 500


class HistoryStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else history_path()
        self._lock = threading.Lock()

    def add(self, source: str, translated: str, target: str, provider: str) -> None:
        entry = {"t": int(time.time()), "src": source, "dst": translated, "target": target, "provider": provider}
        with self._lock:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            self._trim()

    def _trim(self) -> None:
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return
        if len(lines) > MAX_ENTRIES:
            self.path.write_text("\n".join(lines[-MAX_ENTRIES:]) + "\n", encoding="utf-8")

    def entries(self) -> list[dict]:
        with self._lock:
            try:
                lines = self.path.read_text(encoding="utf-8").splitlines()
            except OSError:
                return []
        out = []
        for line in reversed(lines):
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
        return out

    def clear(self) -> None:
        with self._lock:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
