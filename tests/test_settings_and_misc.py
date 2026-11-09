import json

import pytest

from aitranslator.languages import LanguageService
from aitranslator.logging_service import redact
from aitranslator.secure_storage import MemoryBackend, SecureStorage
from aitranslator.settings import SettingsManager
from aitranslator.winplat.hotkey_parse import (
    MOD_ALT, HotkeyParseError, find_duplicates, parse_hotkey,
)


def test_settings_roundtrip_persist(tmp_path):
    path = tmp_path / "s.json"
    m = SettingsManager(path)
    m.settings.languages.preferred_target = "de"
    m.settings.providers.lmstudio.model = "qwen2.5-7b"
    m.settings.providers.active = "lmstudio"
    m.save()
    m2 = SettingsManager(path)  # kapat/aç senaryosu (kabul kriteri 14)
    assert m2.settings.languages.preferred_target == "de"
    assert m2.settings.providers.lmstudio.model == "qwen2.5-7b"
    assert m2.settings.providers.active == "lmstudio"


def test_settings_never_contain_api_keys(tmp_path):
    m = SettingsManager(tmp_path / "s.json")
    m.save()
    raw = (tmp_path / "s.json").read_text()
    assert "api_key" not in raw.lower() and "AIza" not in raw


def test_corrupt_settings_fall_back_to_defaults(tmp_path):
    p = tmp_path / "s.json"
    p.write_text("{ bozuk json")
    m = SettingsManager(p)
    assert m.settings.providers.active == "google"
    assert (tmp_path / "s.corrupt.json").exists()


def test_unknown_and_wrongly_typed_values_ignored(tmp_path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"general": {"notify_on_done": "evet", "yeni_alan": 1}, "providers": {"active": "bilinmeyen"}}))
    m = SettingsManager(p)
    assert m.settings.general.notify_on_done is True
    assert m.settings.providers.active == "google"


def test_hotkey_targets_default_to_preferred(tmp_path):
    m = SettingsManager(tmp_path / "s.json")
    s = m.settings
    s.languages.preferred_target = "en"
    assert s.target_for("alt_b") == "en" and s.target_for("alt_n") == "en" and s.target_for("alt_o") == "en"
    s.languages.alt_n_target = "de"
    assert s.target_for("alt_n") == "de" and s.target_for("alt_b") == "en" and s.target_for("alt_o") == "en"
    s.ocr.target_language = "fr"
    assert s.target_for("alt_o") == "fr"


def test_ocr_settings_roundtrip(tmp_path):
    p = tmp_path / "s.json"
    m = SettingsManager(p)
    m.settings.ocr.engine = "gemini"
    m.settings.ocr.fallback_to_ai = False
    m.settings.ocr.copy_to_clipboard = True
    m.settings.ocr.show_notification = False
    m.settings.ocr.target_language = "ja"
    m.save()

    m2 = SettingsManager(p)
    assert m2.settings.ocr.engine == "gemini"
    assert m2.settings.ocr.fallback_to_ai is False
    assert m2.settings.ocr.copy_to_clipboard is True
    assert m2.settings.ocr.show_notification is False
    assert m2.settings.ocr.target_language == "ja"


def test_parse_hotkey():
    hk = parse_hotkey("Alt+B")
    assert hk.modifiers == MOD_ALT and hk.vk == ord("B")
    assert parse_hotkey("ctrl+shift+f5").normalized() == "Ctrl+Shift+F5"
    for bad in ("", "B", "Alt", "Alt+Ctrl", "Alt+B+N", "Alt+Ünlem"):
        with pytest.raises(HotkeyParseError):
            parse_hotkey(bad)


def test_hotkey_conflict_detection():
    errs = find_duplicates({"alt_b": "Alt+B", "alt_n": "alt+b"})
    assert "alt_n" in errs and "alt_b" not in errs
    assert find_duplicates({"alt_b": "Alt+B", "alt_n": "Alt+N"}) == {}


def test_language_search_turkish_folding():
    names = [c for c, *_ in LanguageService.search("alm")]
    assert "de" in names
    assert "tr" in [c for c, *_ in LanguageService.search("TÜRK")]
    assert LanguageService.normalize("zh") == "zh-CN" and LanguageService.normalize("EN_us") == "en"
    assert LanguageService.guess_language("Günaydın şef") == "tr"


def test_redaction_masks_keys_and_tokens():
    text = "url=https://x/y?key=AIzaSyA1234567890abcdefghijklmnopqrstuv header x-goog-api-key: abc123SECRET Authorization: Bearer sk-ABCDEF1234567890XYZ"
    out = redact(text)
    assert "AIzaSyA1234567890" not in out and "abc123SECRET" not in out and "sk-ABCDEF" not in out


def test_secure_storage_set_get_delete():
    s = SecureStorage(MemoryBackend())
    assert not s.has("gemini_api_key")
    s.set("gemini_api_key", "abc")
    assert s.get("gemini_api_key") == "abc"
    s.set("gemini_api_key", "")
    assert s.get("gemini_api_key") == ""


def test_system_prompt_default_and_custom():
    from aitranslator.providers import DEFAULT_SYSTEM_PROMPT, system_prompt

    # Default prompt with auto-detect
    p_auto = system_prompt("en", "auto")
    assert "Translate the user's text into English." in p_auto
    assert "Detect the source language automatically." in p_auto

    # Default prompt with explicit source
    p_src = system_prompt("de", "tr")
    assert "Translate the user's text into German." in p_src
    assert "The source language is Turkish." in p_src
    assert "If the text is already in German" in p_src

    # Custom prompt with placeholders
    custom = "Custom translation into {target} ({target_code}). Source info: {source} ({source_code})."
    p_custom = system_prompt("fr", "en", custom)
    assert p_custom == "Custom translation into French (fr). Source info: The source language is English. (en)."

    # Custom prompt whitespace falls back to default
    assert system_prompt("en", "auto", "   ") == system_prompt("en", "auto")


def test_settings_roundtrip_persist_prompt(tmp_path):
    path = tmp_path / "s_prompt.json"
    m = SettingsManager(path)
    custom = "Translate to {target} only."
    m.settings.languages.prompt = custom
    m.save()
    m2 = SettingsManager(path)
    assert m2.settings.languages.prompt == custom


def test_settings_window_prompt_box(settings, secrets, tmp_path):
    from PySide6.QtWidgets import QApplication
    from aitranslator.context import AppContext
    from aitranslator.history import HistoryStore
    from aitranslator.providers import DEFAULT_SYSTEM_PROMPT
    from aitranslator.translation_service import TranslationService
    from aitranslator.ui.settings_window import SettingsWindow
    from aitranslator.ui.theme import make_app_icon

    app = QApplication.instance() or QApplication([])
    history = HistoryStore(tmp_path / "h.jsonl")
    translation = TranslationService(settings, secrets, providers={})
    ctx = AppContext(settings, secrets, translation, history, None, lambda: {}, {})
    win = SettingsWindow(ctx, make_app_icon())

    # Initially loaded with default prompt because settings.languages.prompt is empty
    assert win.txt_prompt.toPlainText() == DEFAULT_SYSTEM_PROMPT

    # Edit the prompt in the UI and save
    custom = "Translate into {target}. {source}"
    win.txt_prompt.setPlainText(custom)
    win.save()
    assert settings.settings.languages.prompt == custom

    # Click reset prompt button
    win._reset_prompt()
    assert win.txt_prompt.toPlainText() == DEFAULT_SYSTEM_PROMPT


def test_translation_popup_widget():
    from PySide6.QtWidgets import QApplication
    from aitranslator.ui.popup import TranslationPopup

    app = QApplication.instance() or QApplication([])
    popup = TranslationPopup()
    popup.display("Hello world", "Merhaba dünya", "tr", "Google Translate")
    assert popup.txt_translated.toPlainText() == "Merhaba dünya"
    assert "Türkçe" in popup.lbl_lang.text()
    assert "Google Translate" in popup.lbl_provider.text()
    assert "Hello world" in popup.lbl_orig.text()
    # Test copy button
    popup._copy_translation()
    assert app.clipboard().text() == "Merhaba dünya"
    assert popup.btn_dismiss.text() == "Kapat"
    popup.btn_dismiss.click()
    assert not popup.isVisible()



