import json
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtWidgets import QApplication

from aitranslator.controller import TranslationController
from aitranslator.languages import LanguageService
from aitranslator.settings import SettingsManager
from aitranslator.ui.language_picker import LanguageItemWidget, LanguagePickerManager, LanguagePickerWindow
from aitranslator.ui.settings_window import SettingsWindow
from aitranslator.ui.theme import make_app_icon
from aitranslator.ui.tray import NotificationService, TrayManager
from aitranslator.winplat.hotkey_parse import find_duplicates


def test_hotkey_settings_has_alt_m_default(tmp_path):
    m = SettingsManager(tmp_path / "s.json")
    assert m.settings.hotkeys.alt_m == "Alt+M"
    assert "en" in m.settings.languages.recent_targets


def test_settings_roundtrip_alt_m_and_recent_targets(tmp_path):
    p = tmp_path / "s.json"
    m = SettingsManager(p)
    m.settings.hotkeys.alt_m = "Ctrl+Shift+M"
    m.settings.languages.recent_targets = ["tr", "de", "fr"]
    m.save()

    m2 = SettingsManager(p)
    assert m2.settings.hotkeys.alt_m == "Ctrl+Shift+M"
    assert m2.settings.languages.recent_targets == ["tr", "de", "fr"]


def test_hotkey_conflict_with_alt_m():
    errs = find_duplicates({"alt_b": "Alt+B", "alt_m": "alt+b"})
    assert "alt_m" in errs
    assert find_duplicates({"alt_b": "Alt+B", "alt_n": "Alt+N", "alt_m": "Alt+M"}) == {}


def test_controller_handles_alt_m(settings, secrets, desktop, tmp_path):
    from test_controller_flow import build

    ctl, notes, _ = build(settings, secrets, desktop, tmp_path)
    called = []
    ctl._show_language_picker = lambda: called.append(True)

    # run_job directly
    assert ctl.run_job("alt_m")
    assert len(called) == 1

    # handle_hotkey directly
    ctl.handle_hotkey("alt_m")
    assert len(called) == 2


def test_notification_service_language_picker():
    app = QApplication.instance() or QApplication([])
    notifier = NotificationService()
    called = []
    notifier.language_picker_requested.connect(lambda: called.append(True))
    notifier.show_language_picker()
    assert len(called) == 1


def test_tray_manager_alt_m(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(TrayManager, "available", lambda: True)
    notifier = NotificationService()
    icon = make_app_icon(32)
    tray = TrayManager(icon, False, True, notifier)
    assert "Alt+M" in tray.tray.toolTip()
    called = []
    tray.change_language_requested.connect(lambda: called.append(True))
    tray.change_language_requested.emit()
    assert len(called) == 1


def test_language_picker_window_filtering_and_selection(tmp_path):
    app = QApplication.instance() or QApplication([])
    p = tmp_path / "s.json"
    mgr = SettingsManager(p)
    mgr.settings.languages.preferred_target = "en"
    mgr.settings.languages.alt_b_target = "en"
    mgr.settings.languages.alt_n_target = ""
    mgr.save()

    notifications = []
    changed = []

    def on_notify(t, m, lvl):
        notifications.append((t, m, lvl))

    picker = LanguagePickerWindow(mgr, on_notify, on_language_changed=lambda: changed.append(True))
    picker.open_picker()
    assert picker.isVisible()
    assert "İngilizce" in picker.lbl_current.text()

    # Search for German
    picker.txt_search.setText("alm")
    assert picker.list_widget.count() >= 1
    top_code = picker.list_widget.item(0).data(Qt.ItemDataRole.UserRole)
    assert top_code == "de"

    # Confirm selection of German
    picker._confirm_selection()
    assert not picker.isVisible()

    # Verify settings updated
    # Alt+B hedefi değişir; ana dil (preferred_target) ve Alt+N değişmez
    assert mgr.settings.languages.alt_b_target == "de"
    assert mgr.settings.languages.preferred_target == "en"
    assert mgr.settings.target_for("alt_n") == "en"
    # "de" should now be first in recent_targets
    assert mgr.settings.languages.recent_targets[0] == "de"
    # Callback and notification triggered
    assert len(changed) == 1
    assert len(notifications) == 1
    assert "Almanca" in notifications[0][1]


def test_language_picker_keyboard_navigation_and_cycling(tmp_path):
    app = QApplication.instance() or QApplication([])
    p = tmp_path / "s.json"
    mgr = SettingsManager(p)
    picker = LanguagePickerWindow(mgr, lambda t, m, l: None)

    picker.open_picker()
    assert picker.isVisible()
    initial_row = picker.list_widget.currentRow()

    # Arrow down navigation
    picker._on_navigate(1)
    assert picker.list_widget.currentRow() == initial_row + 1

    # Repeated open_picker while visible cycles to next language
    cur_row = picker.list_widget.currentRow()
    picker.open_picker()
    assert picker.list_widget.currentRow() == (cur_row + 1) % picker.list_widget.count()

    # Escape key hides window
    esc_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    picker.keyPressEvent(esc_event)
    assert not picker.isVisible()


def test_language_picker_manager(tmp_path):
    app = QApplication.instance() or QApplication([])
    p = tmp_path / "s.json"
    mgr = SettingsManager(p)
    lpm = LanguagePickerManager(mgr, lambda t, m, l: None)
    assert lpm._picker is None
    lpm.show_picker()
    assert lpm._picker is not None
    assert lpm._picker.isVisible()
    lpm._picker.hide()


def test_settings_window_hotkeys_includes_alt_m(settings, secrets, tmp_path):
    from aitranslator.context import AppContext
    from aitranslator.history import HistoryStore
    from aitranslator.translation_service import TranslationService

    app = QApplication.instance() or QApplication([])
    history = HistoryStore(tmp_path / "h.jsonl")
    translation = TranslationService(settings, secrets, providers={})
    ctx = AppContext(settings, secrets, translation, history, None, lambda: {}, {})
    win = SettingsWindow(ctx, make_app_icon())

    assert win.key_m.keySequence().toString() == "Alt+M"

    # Set new shortcut in UI
    win.key_m.setKeySequence(QKeySequence("Ctrl+Shift+M"))
    win.save()
    assert settings.settings.hotkeys.alt_m == "Ctrl+Shift+M"

    # Test reset hotkeys
    win._reset_hotkeys()
    assert win.key_m.keySequence().toString() == "Alt+M"
