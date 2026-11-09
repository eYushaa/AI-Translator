"""Uygulama bileşenlerini bir arada tutan (Qt'den bağımsız) bağlam nesnesi."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .controller import TranslationController
from .history import HistoryStore
from .secure_storage import SecureStorage
from .settings import SettingsManager
from .translation_service import TranslationService


@dataclass
class AppContext:
    settings: SettingsManager
    secrets: SecureStorage
    translation: TranslationService
    history: HistoryStore
    controller: TranslationController
    #: bindings sözlüğünü kaydeder ve {ad: hata|None} döner
    apply_hotkeys: Callable[[], dict[str, str | None]]
    hotkey_status: dict[str, str | None]
