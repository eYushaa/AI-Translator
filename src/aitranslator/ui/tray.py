"""TrayManager ve NotificationService (iş parçacığı güvenli)."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .. import APP_NAME
from ..i18n import t


class NotificationService(QObject):
    """Herhangi bir iş parçacığından ``notify``, ``show_popup`` ve ``show_language_picker`` çağrılabilir; gösterim Qt ana iş parçacığında yapılır."""

    message = Signal(str, str, str)
    popup_requested = Signal(str, str, str, str)
    popup_at_requested = Signal(str, str, str, str, object)
    language_picker_requested = Signal()
    ocr_requested = Signal()

    def notify(self, title: str, text: str, level: str = "info") -> None:
        self.message.emit(title, text, level)

    def show_popup(self, original: str, translated: str, target: str, provider: str, pos: object = None) -> None:
        if pos is not None:
            self.popup_at_requested.emit(original, translated, target, provider, pos)
        else:
            self.popup_requested.emit(original, translated, target, provider)

    def show_language_picker(self) -> None:
        self.language_picker_requested.emit()

    def request_ocr(self) -> None:
        self.ocr_requested.emit()



class TrayManager(QObject):
    open_settings = Signal(int)  # sayfa dizini
    change_language_requested = Signal()
    improve_text_requested = Signal()
    fix_grammar_requested = Signal()
    ocr_requested = Signal()
    copy_last_requested = Signal()
    autostart_toggled = Signal(bool)
    hotkeys_toggled = Signal(bool)
    quit_requested = Signal()

    PAGE_GENERAL, PAGE_LANG, PAGE_PROVIDERS, PAGE_HOTKEYS, PAGE_PRIVACY, PAGE_HISTORY = range(6)

    def __init__(self, icon: QIcon, autostart: bool, hotkeys_enabled: bool, notifier: NotificationService) -> None:
        super().__init__()
        self.tray = QSystemTrayIcon(icon)
        self.tray.setToolTip(f"{APP_NAME} – Alt+B / Alt+N / Alt+O / Alt+M / Alt+V / Alt+C")
        menu = QMenu()
        self.act_settings = self._add(menu, t("tray_settings"), lambda: self.open_settings.emit(self.PAGE_GENERAL))
        self.act_ocr = self._add(menu, t("tray_ocr"), self.ocr_requested.emit)
        self.act_change_lang = self._add(menu, t("tray_change_lang"), self.change_language_requested.emit)
        self.act_improve = self._add(menu, t("tray_improve"), self.improve_text_requested.emit)
        self.act_grammar = self._add(menu, t("tray_grammar"), self.fix_grammar_requested.emit)
        self.act_history = self._add(menu, t("tray_history"), lambda: self.open_settings.emit(self.PAGE_HISTORY))
        self.act_hotkeys_page = self._add(menu, t("tray_hotkeys"), lambda: self.open_settings.emit(self.PAGE_HOTKEYS))
        menu.addSeparator()
        self.act_hotkeys = self._add(menu, t("tray_enable_hotkeys"), self.hotkeys_toggled.emit, checkable=True, checked=hotkeys_enabled)
        self.act_autostart = self._add(menu, t("tray_autostart"), self.autostart_toggled.emit, checkable=True, checked=autostart)
        menu.addSeparator()
        self.act_copy_last = self._add(menu, t("tray_copy_last"), self.copy_last_requested.emit)
        menu.addSeparator()
        self.act_quit = self._add(menu, t("tray_quit"), self.quit_requested.emit)
        self._menu = menu
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_activated)
        notifier.message.connect(self.show_message)
        self.tray.show()

    def retranslate(self) -> None:
        self.tray.setToolTip(f"{APP_NAME} – Alt+B / Alt+N / Alt+O / Alt+M / Alt+V / Alt+C")
        self.act_settings.setText(t("tray_settings"))
        self.act_ocr.setText(t("tray_ocr"))
        self.act_change_lang.setText(t("tray_change_lang"))
        self.act_improve.setText(t("tray_improve"))
        self.act_grammar.setText(t("tray_grammar"))
        self.act_history.setText(t("tray_history"))
        self.act_hotkeys_page.setText(t("tray_hotkeys"))
        self.act_hotkeys.setText(t("tray_enable_hotkeys"))
        self.act_autostart.setText(t("tray_autostart"))
        self.act_copy_last.setText(t("tray_copy_last"))
        self.act_quit.setText(t("tray_quit"))

    @staticmethod
    def _add(menu: QMenu, text: str, slot, checkable: bool = False, checked: bool = False) -> QAction:
        act = menu.addAction(text)
        if checkable:
            act.setCheckable(True)
            act.setChecked(checked)
            act.toggled.connect(slot)
        else:
            act.triggered.connect(lambda _=False: slot())
        return act

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.open_settings.emit(self.PAGE_GENERAL)

    def show_message(self, title: str, text: str, level: str = "info") -> None:
        icon = QSystemTrayIcon.MessageIcon.Warning if level == "error" else QSystemTrayIcon.MessageIcon.Information
        self.tray.showMessage(title, text, icon, 5000 if level == "error" else 2500)

    def set_autostart_checked(self, value: bool) -> None:
        self.act_autostart.blockSignals(True)
        self.act_autostart.setChecked(value)
        self.act_autostart.blockSignals(False)

    def set_hotkeys_checked(self, value: bool) -> None:
        self.act_hotkeys.blockSignals(True)
        self.act_hotkeys.setChecked(value)
        self.act_hotkeys.blockSignals(False)

    @staticmethod
    def available() -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def hide(self) -> None:
        self.tray.hide()


def quit_app() -> None:
    QApplication.instance().quit()
