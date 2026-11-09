"""SettingsManager: kullanıcı ayarlarını JSON olarak saklar. API anahtarları burada TUTULMAZ (SecureStorage)."""
from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

from .i18n import normalize_ui_lang, set_ui_language
from .paths import settings_path

PROVIDER_IDS = ("google", "local_llm", "lmstudio", "gemini")
PROVIDER_LABELS = {
    "google": "Google Translate",
    "local_llm": "Yerel LLM (OpenAI uyumlu)",
    "lmstudio": "LM Studio",
    "gemini": "Google Gemini",
}


@dataclass
class GeneralSettings:
    ui_language: str = "tr"
    start_with_windows: bool = False
    minimize_to_tray: bool = True
    notify_on_done: bool = True
    auto_detect_source: bool = True
    keep_original_on_failure: bool = True


@dataclass
class LanguageSettings:
    preferred_target: str = "en"
    alt_b_target: str = ""  # boş = tercih edilen dil
    alt_n_target: str = ""  # boş = tercih edilen dil
    source: str = "auto"
    prompt: str = ""  # boş = varsayılan prompt (DEFAULT_SYSTEM_PROMPT)
    recent_targets: list[str] = field(default_factory=lambda: ["en", "tr", "de", "es", "fr", "ru"])


@dataclass
class EndpointSettings:
    base_url: str = ""
    model: str = ""


@dataclass
class GoogleSettings:
    use_cloud_api: bool = False  # True: resmî Cloud Translation API (anahtar gerekir)


@dataclass
class ProviderSettings:
    active: str = "google"
    auto_fallback: bool = False
    fallback_order: list[str] = field(default_factory=lambda: ["lmstudio", "local_llm", "gemini", "google"])
    timeout_seconds: int = 30
    local_llm: EndpointSettings = field(default_factory=lambda: EndpointSettings("http://localhost:11434/v1", ""))
    lmstudio: EndpointSettings = field(default_factory=lambda: EndpointSettings("http://localhost:1234/v1", ""))
    gemini: EndpointSettings = field(
        default_factory=lambda: EndpointSettings("https://generativelanguage.googleapis.com/v1beta", "gemini-2.5-flash")
    )
    google: GoogleSettings = field(default_factory=GoogleSettings)


@dataclass
class HotkeySettings:
    enabled: bool = True
    alt_b: str = "Alt+B"
    alt_n: str = "Alt+N"
    alt_m: str = "Alt+M"
    alt_v: str = "Alt+V"
    alt_c: str = "Alt+C"
    alt_o: str = "Alt+O"


@dataclass
class OcrSettings:
    engine: str = "auto"  # "auto" (Windows -> Gemini), "windows", "gemini"
    fallback_to_ai: bool = True
    copy_to_clipboard: bool = False
    show_notification: bool = True
    target_language: str = ""  # boş = genel tercih edilen dil


@dataclass
class PrivacySettings:
    history_enabled: bool = False
    cache_enabled: bool = True


@dataclass
class Settings:
    version: int = 1
    general: GeneralSettings = field(default_factory=GeneralSettings)
    languages: LanguageSettings = field(default_factory=LanguageSettings)
    ocr: OcrSettings = field(default_factory=OcrSettings)
    providers: ProviderSettings = field(default_factory=ProviderSettings)
    hotkeys: HotkeySettings = field(default_factory=HotkeySettings)
    privacy: PrivacySettings = field(default_factory=PrivacySettings)

    def target_for(self, hotkey_id: str) -> str:
        if hotkey_id == "alt_b":
            specific = self.languages.alt_b_target
        elif hotkey_id == "alt_n":
            specific = self.languages.alt_n_target
        elif hotkey_id == "alt_o":
            specific = self.ocr.target_language
        else:
            specific = ""
        return specific or self.languages.preferred_target


def _merge(obj: Any, data: dict) -> None:
    """Bilinmeyen/eksik anahtarlara toleranslı yükleme: yalnızca tanımlı alanlar ve doğru tipler alınır."""
    for f in fields(obj):
        if f.name not in data:
            continue
        current = getattr(obj, f.name)
        value = data[f.name]
        if is_dataclass(current):
            if isinstance(value, dict):
                _merge(current, value)
        elif isinstance(current, bool):
            if isinstance(value, bool):
                setattr(obj, f.name, value)
        elif isinstance(current, int):
            if isinstance(value, int) and not isinstance(value, bool):
                setattr(obj, f.name, value)
        elif isinstance(current, str):
            if isinstance(value, str):
                setattr(obj, f.name, value)
        elif isinstance(current, list):
            if isinstance(value, list):
                setattr(obj, f.name, [v for v in value if isinstance(v, str)])


class SettingsManager:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else settings_path()
        self._lock = threading.RLock()
        self.settings = Settings()
        self.load()

    def load(self) -> Settings:
        with self._lock:
            settings = Settings()
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    _merge(settings, data)
            except FileNotFoundError:
                pass
            except (OSError, ValueError):
                # Bozuk dosya: yedekle, varsayılanlarla devam et
                try:
                    self.path.replace(self.path.with_suffix(".corrupt.json"))
                except OSError:
                    pass
            if settings.providers.active not in PROVIDER_IDS:
                settings.providers.active = "google"
            settings.general.ui_language = normalize_ui_lang(settings.general.ui_language)
            set_ui_language(settings.general.ui_language)
            self.settings = settings
            return settings

    def save(self) -> None:
        with self._lock:
            self.settings.general.ui_language = normalize_ui_lang(self.settings.general.ui_language)
            set_ui_language(self.settings.general.ui_language)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(asdict(self.settings), ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, self.path)  # atomik: yarım yazılmış ayar dosyası oluşmaz
