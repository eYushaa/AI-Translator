"""Yeniden kullanılabilir arayüz bileşenleri."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QCompleter, QFrame, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from ..i18n import get_ui_language, t
from ..languages import ENGLISH_NAMES, LANGUAGES, LanguageService


class LanguageCombo(QComboBox):
    """Yazarak aranabilir dil seçici. ``code()`` seçili dil kodunu (veya özel öğenin kodunu) döner."""

    def __init__(self, extra_first: tuple[str, str] | None = None, include_auto: bool = False, extra_first_key: str = "") -> None:
        super().__init__()
        self._extra_first = extra_first
        self._extra_first_key = extra_first_key
        self._include_auto = include_auto
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._populate_items()
        completer = QCompleter(self.model(), self)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setCompleter(completer)
        self.setMaxVisibleItems(14)

    def _populate_items(self) -> None:
        cur_code = self.itemData(self.currentIndex()) if self.count() > 0 else None
        self.blockSignals(True)
        self.clear()
        if self._extra_first is not None:
            first_label = t(self._extra_first_key) if self._extra_first_key else self._extra_first[1]
            self.addItem(first_label, self._extra_first[0])
        if self._include_auto:
            self.addItem(t("auto_detect"), "auto")
        ui_lang = get_ui_language()
        for code, tr, native in LANGUAGES:
            if ui_lang == "tr":
                label = f"{tr} ({native})" if tr != native else tr
            else:
                en = ENGLISH_NAMES.get(code, tr)
                label = f"{native} ({en})" if native != en else native
            self.addItem(f"{label} · {code}", code)
        if cur_code is not None:
            idx = self.findData(cur_code)
            self.setCurrentIndex(idx if idx >= 0 else 0)
        self.blockSignals(False)

    def retranslate(self) -> None:
        self._populate_items()

    def code(self) -> str:
        idx = self.currentIndex()
        if idx >= 0 and self.currentText() == self.itemText(idx):
            return self.itemData(idx)
        found = self.findText(self.currentText(), Qt.MatchFlag.MatchFixedString | Qt.MatchFlag.MatchCaseSensitive)
        return self.itemData(found) if found >= 0 else self.itemData(max(idx, 0))

    def set_code(self, code: str) -> None:
        norm = LanguageService.normalize(code) if code not in ("", "auto") else code
        idx = self.findData(norm)
        self.setCurrentIndex(idx if idx >= 0 else 0)

    def focusOutEvent(self, event) -> None:  # noqa: N802
        super().focusOutEvent(event)
        idx = self.findText(self.currentText(), Qt.MatchFlag.MatchFixedString)
        if idx >= 0:
            self.setCurrentIndex(idx)
        else:  # geçersiz yazı: son geçerli seçime dön
            self.setCurrentIndex(max(self.currentIndex(), 0))
            self.setEditText(self.itemText(self.currentIndex()))


class Card(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Card")
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(18, 16, 18, 16)
        self.root.setSpacing(10)


def title_label(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("Title")
    return lab


def muted_label(text: str, wrap: bool = True) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("Subtle")
    lab.setWordWrap(wrap)
    return lab


def secret_edit(placeholder_when_set: str, is_set: bool) -> QLineEdit:
    edit = QLineEdit()
    edit.setEchoMode(QLineEdit.EchoMode.Password)
    edit.setPlaceholderText(placeholder_when_set if is_set else t("key_placeholder_empty"))
    return edit


def primary_button(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setObjectName("Primary")
    return btn


def padded(widget: QWidget, margins=(28, 24, 28, 24)) -> QWidget:
    holder = QWidget()
    holder.setObjectName("Root")
    lay = QVBoxLayout(holder)
    lay.setContentsMargins(*margins)
    lay.addWidget(widget)
    return holder
