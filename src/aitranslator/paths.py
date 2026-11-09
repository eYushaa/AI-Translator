"""Uygulama veri dizinleri."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from . import APP_NAME


def data_dir() -> Path:
    """Ayar, geçmiş ve günlük dosyalarının tutulduğu dizin (%APPDATA%\\AITranslator)."""
    override = os.environ.get("AITRANSLATOR_HOME")
    if override:
        base = Path(override)
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / APP_NAME
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def settings_path() -> Path:
    return data_dir() / "settings.json"


def history_path() -> Path:
    return data_dir() / "history.jsonl"


def log_path() -> Path:
    return data_dir() / "aitranslator.log"


def secrets_path() -> Path:
    return data_dir() / "secrets.dpapi.json"
