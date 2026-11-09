"""Hızlı Dil Seçici (Quick Language Switcher / Picker): Alt+M ile açılan hedef dil değiştirme penceresi."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QKeyEvent
from PySide6.QtWidgets import (
    QApplication, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget,
)

from ..i18n import get_ui_language, is_rtl, t
from ..languages import LANGUAGES, LanguageService
from ..settings import SettingsManager
from .theme import ACCENT, is_dark, _DARK, _LIGHT


class SearchEdit(QLineEdit):
    """Arama kutusunda yukarı/aşağı ok tuşları ve enter tuşunu yakalayarak listeyle bütünleştirir."""

    navigate_requested = Signal(int)  # +1 (aşağı), -1 (yukarı)
    confirm_requested = Signal()
    cancel_requested = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        key = event.key()
        if key == Qt.Key.Key_Down:
            self.navigate_requested.emit(1)
            event.accept()
        elif key == Qt.Key.Key_Up:
            self.navigate_requested.emit(-1)
            event.accept()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.confirm_requested.emit()
            event.accept()
        elif key == Qt.Key.Key_Escape:
            self.cancel_requested.emit()
            event.accept()
        else:
            super().keyPressEvent(event)


class LanguageItemWidget(QWidget):
    """Dil listesinde her satır için modern, şık kart görünümü."""

    def __init__(
        self,
        code: str,
        tr_name: str,
        native_name: str,
        is_active: bool = False,
        is_recent: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.code = code
        self.is_active = is_active
        c = _DARK if is_dark() else _LIGHT

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)

        # Dil Kodu Rozeti (örn. [TR], [EN], [DE])
        self.badge = QLabel(code.upper())
        self.badge.setFixedWidth(44)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if is_active:
            self.badge.setStyleSheet(f"""
                background-color: {ACCENT};
                color: #FFFFFF;
                font-weight: 700;
                font-size: 8.5pt;
                border-radius: 6px;
                padding: 4px 6px;
            """)
        else:
            self.badge.setStyleSheet(f"""
                background-color: {c['hover']};
                color: {c['text']};
                font-weight: 600;
                font-size: 8.5pt;
                border-radius: 6px;
                padding: 4px 6px;
            """)

        # Dil Adı ve Orijinal Dil Adı
        name_col = QVBoxLayout()
        name_col.setSpacing(2)
        name_col.setContentsMargins(0, 0, 0, 0)

        ui_lang = get_ui_language()
        en_name = LanguageService.english_name(code)
        if ui_lang == "tr":
            primary_name = tr_name
            sub_text = native_name if native_name != tr_name else en_name
        else:
            primary_name = native_name
            sub_text = en_name if native_name != en_name else tr_name

        self.lbl_name = QLabel(primary_name)
        self.lbl_name.setStyleSheet(f"font-weight: {'700' if is_active else '500'}; font-size: 10pt; color: {c['text']};")

        self.lbl_sub = QLabel(sub_text)
        self.lbl_sub.setStyleSheet(f"color: {c['muted']}; font-size: 8.5pt;")

        name_col.addWidget(self.lbl_name)
        if sub_text and sub_text != primary_name:
            name_col.addWidget(self.lbl_sub)

        layout.addWidget(self.badge)
        layout.addLayout(name_col, 1)

        # Durum Göstergesi (Aktif / Son Kullanılan)
        if is_active:
            pill = QLabel(t("picker_badge_active"))
            pill.setStyleSheet(f"""
                background-color: rgba(79, 107, 237, 0.15);
                color: {ACCENT};
                font-weight: 600;
                font-size: 8pt;
                border: 1px solid {ACCENT};
                border-radius: 10px;
                padding: 2px 8px;
            """)
            layout.addWidget(pill)
        elif is_recent:
            recent_lbl = QLabel(t("picker_badge_recent"))
            recent_lbl.setStyleSheet(f"""
                color: {c['muted']};
                font-size: 7.5pt;
                border: 1px solid {c['border']};
                border-radius: 10px;
                padding: 2px 6px;
            """)
            layout.addWidget(recent_lbl)


class LanguagePickerWindow(QWidget):
    """Alt+M ile ekranda beliren modern, klavye dostu hedef dil seçici penceresi."""

    def __init__(
        self,
        settings: SettingsManager,
        notify: Callable[[str, str, str], None],
        on_language_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._notify = notify
        self._on_language_changed = on_language_changed

        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(440, 500)

        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)

        self.card = QFrame()
        self.card.setObjectName("LanguagePickerCard")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 130))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(12)

        # Üst Başlık Satırı
        header = QHBoxLayout()
        header.setSpacing(8)

        self.lbl_title = QLabel(t("picker_title"))
        self.lbl_title.setStyleSheet("font-size: 11pt; font-weight: 700;")

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(26, 26)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.hide)

        header.addWidget(self.lbl_title)
        header.addStretch(1)
        header.addWidget(self.btn_close)
        card_layout.addLayout(header)

        # Mevcut Dil Bilgi Çubuğu
        self.lbl_current = QLabel("")
        self.lbl_current.setStyleSheet("font-size: 9pt;")
        card_layout.addWidget(self.lbl_current)

        # Arama Kutusu
        self.txt_search = SearchEdit()
        self.txt_search.setPlaceholderText(t("picker_search_placeholder"))
        self.txt_search.setClearButtonEnabled(True)
        self.txt_search.textChanged.connect(self._on_search_changed)
        self.txt_search.navigate_requested.connect(self._on_navigate)
        self.txt_search.confirm_requested.connect(self._confirm_selection)
        self.txt_search.cancel_requested.connect(self.hide)
        card_layout.addWidget(self.txt_search)

        # Dil Listesi
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("LanguageList")
        self.list_widget.setFrameShape(QFrame.Shape.NoFrame)
        self.list_widget.setSpacing(2)
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.list_widget.itemDoubleClicked.connect(self._on_item_clicked)
        card_layout.addWidget(self.list_widget, 1)

        # Alt Bilgi / Kısayol İpuçları
        footer = QHBoxLayout()
        footer.setSpacing(8)

        self.lbl_hint = QLabel(t("picker_hint"))
        self.lbl_hint.setStyleSheet("font-size: 8.5pt;")

        self.btn_select = QPushButton(t("picker_btn_select"))
        self.btn_select.setObjectName("Primary")
        self.btn_select.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select.clicked.connect(self._confirm_selection)

        footer.addWidget(self.lbl_hint)
        footer.addStretch(1)
        footer.addWidget(self.btn_select)
        card_layout.addLayout(footer)

        outer.addWidget(self.card)

    def retranslate_ui(self) -> None:
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if is_rtl() else Qt.LayoutDirection.LeftToRight)
        self.lbl_title.setText(t("picker_title"))
        self.txt_search.setPlaceholderText(t("picker_search_placeholder"))
        self.lbl_hint.setText(t("picker_hint"))
        self.btn_select.setText(t("picker_btn_select"))
        self._refresh_current_label()

    def _apply_theme(self) -> None:
        c = _DARK if is_dark() else _LIGHT
        self.card.setStyleSheet(f"""
            #LanguagePickerCard {{
                background-color: {c['card']};
                border: 1px solid {c['border']};
                border-radius: 14px;
            }}
        """)
        self.lbl_title.setStyleSheet(f"font-size: 11.5pt; font-weight: 700; color: {c['text']};")
        self.lbl_current.setStyleSheet(f"color: {c['muted']}; font-size: 9pt;")
        self.lbl_hint.setStyleSheet(f"color: {c['muted']}; font-size: 8.5pt;")
        self.btn_close.setStyleSheet(f"""
            QPushButton {{
                border: none;
                background: transparent;
                color: {c['muted']};
                font-size: 11pt;
                font-weight: bold;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background: {c['hover']};
                color: {c['text']};
            }}
        """)
        self.txt_search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {c['input']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 10pt;
                color: {c['text']};
            }}
            QLineEdit:focus {{
                border: 1.5px solid {ACCENT};
            }}
        """)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                outline: 0;
            }}
            QListWidget::item {{
                border-radius: 8px;
                padding: 1px 0px;
                border: 1px solid transparent;
            }}
            QListWidget::item:hover {{
                background: {c['hover']};
            }}
            QListWidget::item:selected {{
                background: {c['hover']};
                border: 1px solid {ACCENT};
            }}
        """)
        self.btn_select.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT};
                border: 1px solid {ACCENT};
                border-radius: 7px;
                color: #FFFFFF;
                font-weight: 600;
                font-size: 9pt;
                padding: 6px 18px;
            }}
            QPushButton:hover {{
                background-color: #6479F0;
            }}
        """)

    def _refresh_current_label(self) -> None:
        target = self._settings.settings.target_for("alt_b")
        display = LanguageService.display_name(target)
        self.lbl_current.setText(t("picker_current", accent=ACCENT, display=display, code=target.upper()))

    def _refresh_list(self, query: str = "") -> None:
        self.list_widget.clear()
        target = self._settings.settings.target_for("alt_b")
        recent = getattr(self._settings.settings.languages, "recent_targets", [])

        if not query.strip():
            # Arama boşken: önce sık kullanılanlar, sonra tüm liste
            items_to_show: list[tuple[str, str, str, bool]] = []
            seen: set[str] = set()

            # Sık kullanılanlar
            for r_code in recent:
                norm = LanguageService.normalize(r_code)
                for code, tr, native in LANGUAGES:
                    if code == norm and code not in seen:
                        items_to_show.append((code, tr, native, True))
                        seen.add(code)
                        break

            # Geri kalan tüm diller
            for code, tr, native in LANGUAGES:
                if code not in seen:
                    items_to_show.append((code, tr, native, False))
                    seen.add(code)
        else:
            matches = LanguageService.search(query)
            items_to_show = [(c, tr, nat, False) for c, tr, nat in matches]

        selected_row = 0
        for i, (code, tr, native, is_recent) in enumerate(items_to_show):
            item = QListWidgetItem(self.list_widget)
            item.setData(Qt.ItemDataRole.UserRole, code)
            is_active = (code == target)
            if is_active and not query.strip():
                selected_row = i

            widget = LanguageItemWidget(code, tr, native, is_active=is_active, is_recent=is_recent)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(selected_row)
            item = self.list_widget.item(selected_row)
            if item:
                self.list_widget.scrollToItem(item, QListWidget.ScrollHint.PositionAtCenter)

    def _on_search_changed(self, text: str) -> None:
        self._refresh_list(text)

    def _on_navigate(self, step: int) -> None:
        count = self.list_widget.count()
        if count == 0:
            return
        cur = self.list_widget.currentRow()
        new_row = max(0, min(count - 1, cur + step))
        self.list_widget.setCurrentRow(new_row)
        item = self.list_widget.item(new_row)
        if item:
            self.list_widget.scrollToItem(item)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        code = item.data(Qt.ItemDataRole.UserRole)
        if code:
            self.select_language(code)

    def _confirm_selection(self) -> None:
        item = self.list_widget.currentItem()
        if item:
            code = item.data(Qt.ItemDataRole.UserRole)
            if code:
                self.select_language(code)

    def select_language(self, code: str) -> None:
        """Alt+B (yazdığınızı çevir) hedef dilini günceller; ana dil (Alt+N) değişmez."""
        s = self._settings.settings
        s.languages.alt_b_target = code

        # Sık kullanılanlar listesini güncelle
        if hasattr(s.languages, "recent_targets"):
            recents = s.languages.recent_targets
            if code in recents:
                recents.remove(code)
            recents.insert(0, code)
            s.languages.recent_targets = recents[:8]

        self._settings.save()

        if self._on_language_changed:
            try:
                self._on_language_changed()
            except Exception:
                pass

        disp = LanguageService.display_name(code)
        self._notify(t("notify_lang_changed_title"), t("notify_lang_changed_msg", display=disp), "info")
        self.hide()

    def open_picker(self) -> None:
        """Pencereyi açar veya açıksa bir sonraki dile geçer (Alt+M döngüsü)."""
        if self.isVisible():
            # Zaten açıksa: bir sonraki dile atla
            count = self.list_widget.count()
            if count > 1:
                cur = self.list_widget.currentRow()
                next_row = (cur + 1) % count
                self.list_widget.setCurrentRow(next_row)
                item = self.list_widget.item(next_row)
                if item:
                    self.list_widget.scrollToItem(item)
            return

        self._apply_theme()
        self.retranslate_ui()
        self.txt_search.blockSignals(True)
        self.txt_search.clear()
        self.txt_search.blockSignals(False)
        self._refresh_list("")

        self._position_window()
        self.show()
        self.raise_()
        self.activateWindow()

        # Windows'ta ön plana alma ve odağı garanti etme
        try:
            import ctypes
            ctypes.windll.user32.SetForegroundWindow(int(self.winId()))
        except Exception:
            pass

        self.txt_search.setFocus()
        self.txt_search.selectAll()

    def _position_window(self) -> None:
        """Pencereyi imlecin bulunduğu monitörün hafif üst-orta (HUD / Spotlight) konumuna yerleştirir."""
        cursor_pos = QCursor.pos()
        screen = QGuiApplication.screenAt(cursor_pos) or QGuiApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.left() + (geo.width() - self.width()) // 2
            y = geo.top() + int((geo.height() - self.height()) * 0.35)
            self.move(QPoint(x, y))

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            event.accept()
        else:
            super().keyPressEvent(event)


class LanguagePickerManager:
    """İş parçacığı ve Qt sinyalleri üzerinden çağrılan tekil picker yöneticisi."""

    def __init__(
        self,
        settings: SettingsManager,
        notify: Callable[[str, str, str], None],
        on_language_changed: Callable[[], None] | None = None,
    ) -> None:
        self._settings = settings
        self._notify = notify
        self._on_language_changed = on_language_changed
        self._picker: LanguagePickerWindow | None = None

    def show_picker(self) -> None:
        if self._picker is None:
            self._picker = LanguagePickerWindow(self._settings, self._notify, self._on_language_changed)
        self._picker.open_picker()

    def retranslate_ui(self) -> None:
        if self._picker is not None:
            self._picker.retranslate_ui()
