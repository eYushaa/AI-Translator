from unittest.mock import MagicMock
import pytest
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QFont, QImage, QKeyEvent, QKeySequence, QPainter
from PySide6.QtWidgets import QApplication

from aitranslator.context import AppContext
from aitranslator.controller import TranslationController
from aitranslator.history import HistoryStore
from aitranslator.ocr import OcrService, qimage_to_png_bytes
from aitranslator.replacement import TextReplacementService
from aitranslator.selection import TextSelectionService
from aitranslator.settings import SettingsManager
from aitranslator.translation_service import TranslationService
from aitranslator.ui.settings_window import SettingsWindow
from aitranslator.ui.snipper import ScreenSnipperManager, ScreenSnipperOverlay
from aitranslator.ui.theme import make_app_icon
from aitranslator.ui.tray import NotificationService, TrayManager
from test_translation_service import Stub


def _create_test_image(text: str = "Test Text") -> QImage:
    app = QApplication.instance() or QApplication([])
    img = QImage(300, 100, QImage.Format.Format_RGBA8888)
    img.fill(QColor(255, 255, 255))
    p = QPainter(img)
    p.setPen(QColor(0, 0, 0))
    p.setFont(QFont("Arial", 20))
    p.drawText(20, 50, text)
    p.end()
    return img


def test_qimage_to_png_bytes():
    img = _create_test_image("PNG")
    data = qimage_to_png_bytes(img)
    assert len(data) > 0
    assert data.startswith(b"\x89PNG\r\n\x1a\n")


def test_ocr_service_empty_image():
    ocr = OcrService()
    assert ocr.extract_text(QImage()) == ""
    tiny = QImage(2, 2, QImage.Format.Format_RGBA8888)
    assert ocr.extract_text(tiny) == ""


def test_ocr_service_real_winocr():
    img = _create_test_image("Hello from OCR Test!")
    ocr = OcrService()
    text = ocr.extract_text(img)
    # Windows OCR is available on this Windows environment
    assert len(text) > 0
    assert "Hello" in text or "He" in text


def test_ocr_service_with_gemini_fallback(monkeypatch):
    ocr = OcrService()
    # Mock _extract_with_winocr to return empty
    monkeypatch.setattr(ocr, "_extract_with_winocr", lambda img, hint: "")

    # Mock gemini provider
    mock_gemini = MagicMock()
    mock_gemini.is_configured.return_value = True
    mock_gemini.base_url = "https://api"
    mock_gemini.model = "gemini-2.5-flash"
    mock_gemini._headers.return_value = {}

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "Extracted from Gemini"}]}}]
    }
    mock_gemini.request.return_value = mock_resp

    ocr._gemini = mock_gemini
    img = _create_test_image("Gemini Image")
    result = ocr.extract_text(img)
    assert result == "Extracted from Gemini"


def test_hotkey_settings_has_alt_o_default(tmp_path):
    m = SettingsManager(tmp_path / "s.json")
    assert m.settings.hotkeys.alt_o == "Alt+O"

    m.settings.hotkeys.alt_o = "Ctrl+Shift+O"
    m.save()

    m2 = SettingsManager(tmp_path / "s.json")
    assert m2.settings.hotkeys.alt_o == "Ctrl+Shift+O"


def test_controller_handles_alt_o(settings, secrets, desktop, tmp_path):
    from test_controller_flow import build

    ctl, notes, _ = build(settings, secrets, desktop, tmp_path)
    called = []
    ctl._request_ocr = lambda: called.append(True)

    assert ctl.run_job("alt_o")
    assert len(called) == 1

    ctl.handle_hotkey("alt_o")
    assert len(called) == 2


def test_controller_process_ocr_image_end_to_end(settings, secrets, desktop, tmp_path):
    popups = []
    notes = []
    google = Stub("google", result="Hello from OCR translated")
    svc = TranslationService(settings, secrets, providers={"google": google})
    sel = TextSelectionService(desktop.clipboard, desktop, desktop, sleep=lambda s: None, copy_timeout=0.2)
    rep = TextReplacementService(desktop.clipboard, desktop, desktop, sleep=lambda s: None)

    mock_ocr = MagicMock()
    mock_ocr.extract_text.return_value = "Bonjour monde"

    ctl = TranslationController(
        settings,
        svc,
        sel,
        rep,
        HistoryStore(tmp_path / "h.jsonl"),
        lambda t, m, l: notes.append((t, m, l)),
        show_popup=lambda orig, trans, tgt, prov, pos=None: popups.append((orig, trans, tgt, prov, pos)),
        ocr_service=mock_ocr,
    )

    img = _create_test_image("Bonjour monde")
    pos = QPoint(500, 300)

    # Run OCR job synchronously
    ok = ctl._run_ocr_job(img, pos)
    assert ok
    assert len(popups) == 1
    assert popups[0][0] == "Bonjour monde"
    assert popups[0][1] == "Hello from OCR translated"
    assert "OCR" in popups[0][3]
    assert popups[0][4] == pos
    assert ctl.last_translation == "Hello from OCR translated"


def test_controller_process_ocr_image_empty(settings, secrets, desktop, tmp_path):
    popups = []
    notes = []
    google = Stub("google", result="Hello")
    svc = TranslationService(settings, secrets, providers={"google": google})
    sel = TextSelectionService(desktop.clipboard, desktop, desktop, sleep=lambda s: None, copy_timeout=0.2)
    rep = TextReplacementService(desktop.clipboard, desktop, desktop, sleep=lambda s: None)

    mock_ocr = MagicMock()
    mock_ocr.extract_text.return_value = "   "

    ctl = TranslationController(
        settings,
        svc,
        sel,
        rep,
        HistoryStore(tmp_path / "h.jsonl"),
        lambda t, m, l: notes.append((t, m, l)),
        show_popup=lambda orig, trans, tgt, prov, pos=None: popups.append((orig, trans, tgt, prov, pos)),
        ocr_service=mock_ocr,
    )

    img = _create_test_image("Empty")
    ok = ctl._run_ocr_job(img)
    assert not ok
    assert len(popups) == 0
    assert any("bulunamadı" in n[0].lower() or "not found" in n[0].lower() for n in notes)


def test_settings_window_hotkey_alt_o(settings, secrets, tmp_path):
    app = QApplication.instance() or QApplication([])
    history = HistoryStore(tmp_path / "h.jsonl")
    translation = TranslationService(settings, secrets, providers={})
    ctx = AppContext(settings, secrets, translation, history, None, lambda: {}, {})
    win = SettingsWindow(ctx, make_app_icon())

    assert win.key_o.keySequence().toString() == "Alt+O"

    win.key_o.setKeySequence(QKeySequence("Ctrl+Shift+O"))
    win.save()
    assert settings.settings.hotkeys.alt_o == "Ctrl+Shift+O"

    win._reset_hotkeys()
    assert win.key_o.keySequence().toString() == "Alt+O"


def test_tray_manager_has_ocr(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(TrayManager, "available", lambda: True)
    notifier = NotificationService()
    icon = make_app_icon(32)
    tray = TrayManager(icon, False, True, notifier)

    assert "Alt+O" in tray.tray.toolTip()
    assert "OCR" in tray.act_ocr.text()

    called = []
    tray.ocr_requested.connect(lambda: called.append(True))
    tray.act_ocr.trigger()
    assert len(called) == 1


def test_screen_snipper_overlay_lifecycle():
    app = QApplication.instance() or QApplication([])
    captured = []
    snipper = ScreenSnipperOverlay()
    snipper.snippet_captured.connect(lambda img, pos: captured.append((img, pos)))

    snipper.start_capture()
    assert snipper.isVisible()

    # Escape cancels snipper
    esc = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    snipper.keyPressEvent(esc)
    assert not snipper.isVisible()
    assert len(captured) == 0


def test_screen_snipper_manager():
    app = QApplication.instance() or QApplication([])
    captured = []
    manager = ScreenSnipperManager(lambda img, pos: captured.append((img, pos)))
    assert manager._snipper is None

    manager.start_snip()
    assert manager._snipper is not None
    assert manager._snipper.isVisible()
    manager._snipper.close()


def test_ocr_installed_languages():
    langs = OcrService.get_installed_windows_ocr_languages()
    assert isinstance(langs, list)


def test_ocr_engine_options(monkeypatch):
    ocr = OcrService()
    gemini_mock = MagicMock()
    gemini_mock.is_configured.return_value = True
    ocr._gemini = gemini_mock

    # Mock _extract_with_gemini and _extract_with_winocr
    monkeypatch.setattr(ocr, "_extract_with_winocr", lambda img, hint: "Windows Text")
    monkeypatch.setattr(ocr, "_extract_with_gemini", lambda img: "Gemini Text")

    img = _create_test_image("Hello")

    # engine='gemini' -> directly gemini
    assert ocr.extract_text(img, engine="gemini") == "Gemini Text"

    # engine='windows' -> winocr
    assert ocr.extract_text(img, engine="windows") == "Windows Text"

    # engine='windows' with empty winocr and fallback_to_ai=False -> empty
    monkeypatch.setattr(ocr, "_extract_with_winocr", lambda img, hint: "")
    assert ocr.extract_text(img, engine="windows", fallback_to_ai=False) == ""

    # engine='windows' with empty winocr and fallback_to_ai=True -> gemini
    assert ocr.extract_text(img, engine="windows", fallback_to_ai=True) == "Gemini Text"


def test_settings_window_ocr_tab_and_bottom_language_bar(tmp_path):
    app = QApplication.instance() or QApplication([])
    sm = SettingsManager(tmp_path / "s.json")
    ctx = AppContext(
        settings=sm,
        secrets=MagicMock(),
        translation=MagicMock(),
        history=MagicMock(),
        controller=None,
        apply_hotkeys=lambda: {},
        hotkey_status={},
    )
    win = SettingsWindow(ctx, make_app_icon(32))

    # 1. Sol panel en altta dil değiştirme çubuğu
    assert hasattr(win, "left_panel")
    assert hasattr(win, "sidebar_bottom")
    assert win.cmb_ui_lang.count() == 10
    assert win.lbl_ui_lang.text().startswith("🌐")

    # 2. OCR sayfası ve seçenekleri
    from aitranslator.ui.settings_window import PAGE_KEYS
    assert "page_ocr" in PAGE_KEYS
    ocr_idx = PAGE_KEYS.index("page_ocr")

    win.sidebar.setCurrentRow(ocr_idx)
    assert win.stack.currentIndex() == ocr_idx

    assert hasattr(win, "cmb_ocr_engine")
    assert hasattr(win, "chk_ocr_fallback")
    assert hasattr(win, "chk_ocr_clipboard")
    assert hasattr(win, "chk_ocr_notify")
    assert hasattr(win, "cmb_ocr_target")
    assert hasattr(win, "btn_ocr_hotkey")

    # Kısayol değiştir butonuna tıklayınca Kısayollar sekmesine yönlenmeli
    win.btn_ocr_hotkey.click()
    assert win.sidebar.currentRow() == PAGE_KEYS.index("page_hotkeys")

    # Verify cmb_ocr_target code defaults to "" (not "af")
    assert win.cmb_ocr_target.code() == ""
    win.retranslate_ui()
    assert win.cmb_ocr_target.code() == ""

    # Form okuma ve yükleme
    win.cmb_ocr_engine.setCurrentIndex(1)  # windows
    win.chk_ocr_fallback.setChecked(False)
    win.chk_ocr_clipboard.setChecked(True)
    win.chk_ocr_notify.setChecked(False)
    win.save()

    assert sm.settings.ocr.engine == "windows"
    assert sm.settings.ocr.fallback_to_ai is False
    assert sm.settings.ocr.copy_to_clipboard is True
    assert sm.settings.ocr.show_notification is False

    from aitranslator.ui.language_picker import LanguagePickerManager
    lpm = LanguagePickerManager(sm, MagicMock())
    lpm.retranslate_ui()  # Should not raise AttributeError even if picker is None

