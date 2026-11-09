"""Uygulama kompozisyon kökü: servisleri kurar, tepsiyi, kısayolları ve ayar penceresini bağlar."""
from __future__ import annotations

import sys

from PySide6.QtCore import QObject
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox

from . import APP_NAME, autostart
from .context import AppContext
from .controller import TranslationController
from .history import HistoryStore
from .i18n import t
from .logging_service import get_logger, setup_logging
from .replacement import TextReplacementService
from .secure_storage import SecureStorage
from .selection import TextSelectionService
from .settings import SettingsManager
from .translation_service import TranslationService
from .ui.language_picker import LanguagePickerManager
from .ui.popup import TranslationPopupManager
from .ui.settings_window import SettingsWindow
from .ui.snipper import ScreenSnipperManager
from .ui.theme import apply_theme, make_app_icon
from .ui.tray import NotificationService, TrayManager
from .winplat.clipboard import ClipboardManager
from .winplat.hotkeys import HotkeyManager
from .winplat.windows_io import WindowsInspector, WindowsKeyboard

IPC_NAME = "AITranslator.SingleInstance.v1"
log = get_logger("app")


def _signal_running_instance() -> bool:
    """Zaten çalışan bir örnek varsa ona 'göster' mesajı yollar ve True döner."""
    sock = QLocalSocket()
    sock.connectToServer(IPC_NAME)
    if sock.waitForConnected(300):
        sock.write(b"show")
        sock.waitForBytesWritten(300)
        sock.disconnectFromServer()
        return True
    return False


def run(argv: list[str]) -> int:
    setup_logging()
    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    apply_theme(app)
    icon = make_app_icon()
    app.setWindowIcon(icon)

    # ---- tek örnek ----
    if _signal_running_instance():
        return 0
    QLocalServer.removeServer(IPC_NAME)  # çökme sonrası kalan eski kayıt
    server = QLocalServer()
    server.listen(IPC_NAME)

    background = "--background" in argv

    # ---- servisler ----
    settings = SettingsManager()
    first_run = not settings.path.exists()
    secrets = SecureStorage()
    translation = TranslationService(settings, secrets)
    history = HistoryStore()
    notifier = NotificationService()
    popup_manager = TranslationPopupManager()
    notifier.popup_requested.connect(popup_manager.show_popup)
    notifier.popup_at_requested.connect(lambda o, tr, tgt, prov, pos: popup_manager.show_popup(o, tr, tgt, prov, pos))
    clipboard = ClipboardManager()
    keyboard = WindowsKeyboard()
    inspector = WindowsInspector()
    selection = TextSelectionService(clipboard, keyboard, inspector)
    replacement = TextReplacementService(clipboard, keyboard, inspector)
    controller = TranslationController(
        settings,
        translation,
        selection,
        replacement,
        history,
        notifier.notify,
        notifier.show_popup,
        show_language_picker=notifier.show_language_picker,
        request_ocr=notifier.request_ocr,
    )
    snipper = ScreenSnipperManager(controller.process_ocr_image)
    notifier.ocr_requested.connect(snipper.start_snip)
    hotkeys = HotkeyManager(controller.handle_hotkey)

    def apply_hotkeys() -> dict[str, str | None]:
        s = settings.settings
        try:
            result = hotkeys.apply(
                {
                    "alt_b": s.hotkeys.alt_b,
                    "alt_n": s.hotkeys.alt_n,
                    "alt_m": s.hotkeys.alt_m,
                    "alt_v": s.hotkeys.alt_v,
                    "alt_c": s.hotkeys.alt_c,
                    "alt_o": s.hotkeys.alt_o,
                },
                s.hotkeys.enabled,
            )
        except OSError:
            msg = "Genel kısayollar yalnızca Windows'ta çalışır."
            result = {"alt_b": msg, "alt_n": msg, "alt_m": msg, "alt_v": msg, "alt_c": msg, "alt_o": msg}
        for msg in result.values():
            if msg:
                notifier.notify(t("notify_hk_warn"), msg, "error")
        return result

    ctx = AppContext(settings, secrets, translation, history, controller, apply_hotkeys, {})
    window = SettingsWindow(ctx, icon)
    language_picker = LanguagePickerManager(
        settings, notifier.notify, on_language_changed=window.load_from_settings
    )
    notifier.language_picker_requested.connect(language_picker.show_picker)

    tray_ok = TrayManager.available()
    tray = TrayManager(icon, settings.settings.general.start_with_windows, settings.settings.hotkeys.enabled, notifier) if tray_ok else None

    # UI dili değiştiğinde tray ve picker bileşenlerini güncelle
    window.ui_language_changed.connect(lambda _lang: tray.retranslate() if tray else None)
    window.ui_language_changed.connect(lambda _lang: language_picker.retranslate_ui())

    # Kayıt defterindeki başlangıç girdisini ayarla eşitle (yol değişimlerini de düzeltir)
    try:
        autostart.set_enabled(settings.settings.general.start_with_windows)
    except OSError:
        log.warning("Başlangıç girdisi eşitlenemedi")

    # ---- olaylar ----
    def show_page(index: int) -> None:
        window.show_page(index)

    def copy_last() -> None:
        if controller.last_translation:
            app.clipboard().setText(controller.last_translation)
            notifier.notify(t("notify_copied_title"), t("notify_copied_msg"), "info")
        else:
            notifier.notify(t("notify_no_copy_title"), t("notify_no_copy_msg"), "info")

    def set_autostart(value: bool) -> None:
        settings.settings.general.start_with_windows = value
        settings.save()
        try:
            autostart.set_enabled(value)
        except OSError as exc:
            notifier.notify(t("err_autostart_title"), t("err_autostart_msg", exc=exc), "error")
        window.load_from_settings()

    def set_hotkeys(value: bool) -> None:
        settings.settings.hotkeys.enabled = value
        settings.save()
        ctx.hotkey_status.clear()
        ctx.hotkey_status.update(apply_hotkeys())
        window.load_from_settings()

    def quit_now() -> None:
        window.really_quit = True
        hotkeys.stop()
        if tray:
            tray.hide()
        server.close()
        app.quit()

    if tray:
        tray.open_settings.connect(show_page)
        tray.ocr_requested.connect(snipper.start_snip)
        tray.change_language_requested.connect(notifier.show_language_picker)
        tray.improve_text_requested.connect(lambda: controller.handle_hotkey("alt_v"))
        tray.fix_grammar_requested.connect(lambda: controller.handle_hotkey("alt_c"))
        tray.copy_last_requested.connect(copy_last)
        tray.autostart_toggled.connect(set_autostart)
        tray.hotkeys_toggled.connect(set_hotkeys)
        tray.quit_requested.connect(quit_now)
    else:
        notifier.message.connect(lambda t, m, lvl: QMessageBox.information(window, t, m) if lvl == "error" else None)
        settings.settings.general.minimize_to_tray = False

    def on_ipc() -> None:
        conn = server.nextPendingConnection()
        if conn:
            conn.readyRead.connect(lambda: (conn.readAll(), show_page(0)))

    server.newConnection.connect(on_ipc)

    ctx.hotkey_status.update(apply_hotkeys())
    if not (background and tray) or first_run:
        window.show()
    if first_run:
        settings.save()
        notifier.notify(
            APP_NAME,
            t("notify_ready_msg"),
            "info",
        )
    app.aboutToQuit.connect(hotkeys.stop)
    return app.exec()


def main(argv: list[str] | None = None) -> int:
    return run(argv if argv is not None else sys.argv)
