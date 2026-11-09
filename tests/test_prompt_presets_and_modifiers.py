import pytest
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication

from aitranslator.context import AppContext
from aitranslator.controller import TranslationController
from aitranslator.history import HistoryStore
from aitranslator.providers import (
    DEFAULT_SYSTEM_PROMPT,
    GRAMMAR_FIX_PROMPT,
    IMPROVE_TEXT_PROMPT,
    PROMPT_PRESETS,
    GeminiProvider,
)
from aitranslator.replacement import TextReplacementService
from aitranslator.selection import TextSelectionService
from aitranslator.settings import SettingsManager
from aitranslator.translation_service import TranslationError, TranslationService
from aitranslator.ui.settings_window import SettingsWindow
from aitranslator.ui.theme import make_app_icon
from test_translation_service import Stub


def test_prompt_presets_contain_all_modes():
    labels = [label for label, _ in PROMPT_PRESETS]
    assert any("Standart" in l for l in labels)
    assert any("Resmi" in l for l in labels)
    assert any("Günlük" in l for l in labels)
    assert any("Akademik" in l for l in labels)
    assert any("İyileştirme" in l for l in labels)
    assert any("İmla" in l for l in labels)
    assert any("Özet" in l for l in labels)


def test_settings_window_prompt_presets_combobox(settings, secrets, tmp_path):
    app = QApplication.instance() or QApplication([])
    history = HistoryStore(tmp_path / "h.jsonl")
    translation = TranslationService(settings, secrets, providers={})
    ctx = AppContext(settings, secrets, translation, history, None, lambda: {}, {})
    win = SettingsWindow(ctx, make_app_icon())

    # ComboBox should be present and have presets
    assert win.cmb_prompt_presets.count() == len(PROMPT_PRESETS) + 1
    # Initially default preset matches
    assert win.cmb_prompt_presets.currentIndex() == 1

    # Select "Resmi ve Kurumsal Çeviri" (index 2)
    win.cmb_prompt_presets.setCurrentIndex(2)
    assert "corporate translator" in win.txt_prompt.toPlainText().lower()

    # User manually types something custom
    win.txt_prompt.setPlainText("Benim özel promptum: {target}")
    assert win.cmb_prompt_presets.currentIndex() == 0  # Özel

    # Reset button restores default preset
    win._reset_prompt()
    assert win.cmb_prompt_presets.currentIndex() == 1
    assert win.txt_prompt.toPlainText() == DEFAULT_SYSTEM_PROMPT


def test_settings_window_hotkeys_alt_v_alt_c(settings, secrets, tmp_path):
    app = QApplication.instance() or QApplication([])
    history = HistoryStore(tmp_path / "h.jsonl")
    translation = TranslationService(settings, secrets, providers={})
    ctx = AppContext(settings, secrets, translation, history, None, lambda: {}, {})
    win = SettingsWindow(ctx, make_app_icon())

    assert win.key_v.keySequence().toString() == "Alt+V"
    assert win.key_c.keySequence().toString() == "Alt+C"

    # Modify and save
    win.key_v.setKeySequence(QKeySequence("Ctrl+Shift+V"))
    win.key_c.setKeySequence(QKeySequence("Ctrl+Shift+C"))
    win.save()
    assert settings.settings.hotkeys.alt_v == "Ctrl+Shift+V"
    assert settings.settings.hotkeys.alt_c == "Ctrl+Shift+C"

    # Reset hotkeys
    win._reset_hotkeys()
    assert win.key_v.keySequence().toString() == "Alt+V"
    assert win.key_c.keySequence().toString() == "Alt+C"


def test_controller_alt_v_improves_text(settings, secrets, desktop, tmp_path):
    # Setup LLM stub for gemini
    llm = Stub("gemini", result="Geliştirilmiş ve akıcı metin.")
    svc = TranslationService(settings, secrets, providers={"gemini": llm, "google": Stub("google")})
    settings.settings.providers.active = "gemini"

    sel = TextSelectionService(desktop.clipboard, desktop, desktop, sleep=lambda s: None, copy_timeout=0.2)
    rep = TextReplacementService(desktop.clipboard, desktop, desktop, sleep=lambda s: None)
    notes = []
    ctl = TranslationController(
        settings, svc, sel, rep, HistoryStore(tmp_path / "h.jsonl"),
        lambda t, m, l: notes.append((t, m, l)),
    )

    desktop.text = "ben buraya geldim ama hic guzel degildi."
    desktop.sel = [0, len(desktop.text)]

    ok = ctl.run_job("alt_v")
    assert ok
    assert desktop.text == "Geliştirilmiş ve akıcı metin."
    assert any(n[0] == "Metin iyileştirildi" for n in notes)


def test_controller_alt_c_fixes_grammar(settings, secrets, desktop, tmp_path):
    llm = Stub("gemini", result="Ben buraya geldim ama hiç güzel değildi.")
    svc = TranslationService(settings, secrets, providers={"gemini": llm, "google": Stub("google")})
    settings.settings.providers.active = "gemini"

    sel = TextSelectionService(desktop.clipboard, desktop, desktop, sleep=lambda s: None, copy_timeout=0.2)
    rep = TextReplacementService(desktop.clipboard, desktop, desktop, sleep=lambda s: None)
    notes = []
    ctl = TranslationController(
        settings, svc, sel, rep, HistoryStore(tmp_path / "h.jsonl"),
        lambda t, m, l: notes.append((t, m, l)),
    )

    desktop.text = "ben buraya geldım ama hıc guzel degıldı."
    desktop.sel = [0, len(desktop.text)]

    ok = ctl.run_job("alt_c")
    assert ok
    assert desktop.text == "Ben buraya geldim ama hiç güzel değildi."
    assert any(n[0] == "İmla düzeltildi" for n in notes)


def test_translation_service_prompt_override_requires_llm(settings, secrets):
    # Only google configured
    settings.settings.providers.active = "google"
    google_stub = Stub("google", result="sabit")
    svc = TranslationService(settings, secrets, providers={"google": google_stub})

    # When prompt_override is passed with only google available, it raises TranslationError
    with pytest.raises(TranslationError) as exc:
        svc.translate("test", "auto", prompt_override=IMPROVE_TEXT_PROMPT)
    assert "LLM" in exc.value.message or "Gemini" in exc.value.message
