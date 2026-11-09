"""Çeviri Kutucuğu (Popup / Floating Tooltip): Alt+N ile seçilen metnin çevirisini modern ve şık bir kutucukta gösterir."""
from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QGuiApplication
from PySide6.QtWidgets import (
    QApplication, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QVBoxLayout, QWidget,
)

from ..i18n import is_rtl, t
from ..languages import LanguageService
from .theme import ACCENT, is_dark, _DARK, _LIGHT


class TranslationPopup(QWidget):
    """İmlecin yanında beliren şık, kenarlıksız, gölgeli çeviri kutucuğu."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(420)

        # Otomatik kapanma zamanlayıcısı (20 saniye)
        self._auto_close_timer = QTimer(self)
        self._auto_close_timer.setInterval(20000)
        self._auto_close_timer.timeout.connect(self.hide)

        self._translated_text = ""
        self._build_ui()

    def _build_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(12, 12, 12, 12)

        self.card = QFrame()
        self.card.setObjectName("PopupCard")

        # Yumuşak gölge efekti
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 110))
        shadow.setOffset(0, 6)
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)

        # Üst çubuk: Dil etiketi, sağlayıcı ve kapatma butonu
        header = QHBoxLayout()
        header.setSpacing(8)

        self.lbl_lang = QLabel(t("popup_title"))
        self.lbl_provider = QLabel("")

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.hide)

        header.addWidget(self.lbl_lang)
        header.addWidget(self.lbl_provider)
        header.addStretch(1)
        header.addWidget(self.btn_close)
        card_layout.addLayout(header)

        # Orijinal metin önizlemesi (kısa)
        self.lbl_orig = QLabel("")
        self.lbl_orig.setWordWrap(True)
        self.lbl_orig.setMaximumHeight(42)
        card_layout.addWidget(self.lbl_orig)

        # Çeviri metni kutusu
        self.txt_translated = QTextEdit()
        self.txt_translated.setReadOnly(True)
        self.txt_translated.setFrameStyle(QFrame.Shape.NoFrame)
        self.txt_translated.setMinimumHeight(65)
        self.txt_translated.setMaximumHeight(240)
        self.txt_translated.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        card_layout.addWidget(self.txt_translated)

        # Alt çubuk: Kopyala butonu, Kapat butonu ve kısayol ipucu
        footer = QHBoxLayout()
        footer.setSpacing(8)

        self.btn_copy = QPushButton(t("popup_btn_copy"))
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.clicked.connect(self._copy_translation)

        self.btn_dismiss = QPushButton(t("popup_btn_dismiss"))
        self.btn_dismiss.setObjectName("BtnDismiss")
        self.btn_dismiss.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dismiss.setToolTip(t("popup_tooltip_dismiss"))
        self.btn_dismiss.clicked.connect(self.hide)

        self.lbl_hint = QLabel(t("popup_hint"))

        footer.addWidget(self.btn_copy)
        footer.addWidget(self.btn_dismiss)
        footer.addStretch(1)
        footer.addWidget(self.lbl_hint)
        card_layout.addLayout(footer)

        outer_layout.addWidget(self.card)

    def _apply_theme(self) -> None:
        c = _DARK if is_dark() else _LIGHT
        self.card.setStyleSheet(f"""
            #PopupCard {{
                background-color: {c['card']};
                border: 1px solid {c['border']};
                border-radius: 12px;
            }}
        """)
        self.lbl_lang.setStyleSheet(f"""
            background-color: {ACCENT};
            color: #FFFFFF;
            border-radius: 6px;
            padding: 3px 8px;
            font-weight: 600;
            font-size: 8.5pt;
        """)
        self.lbl_provider.setStyleSheet(f"""
            background-color: {c['hover']};
            color: {c['muted']};
            border-radius: 6px;
            padding: 3px 7px;
            font-size: 8.5pt;
        """)
        self.btn_close.setStyleSheet(f"""
            QPushButton {{
                border: none;
                background: transparent;
                color: {c['muted']};
                font-size: 11pt;
                font-weight: bold;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background: {c['hover']};
                color: {c['text']};
            }}
        """)
        self.lbl_orig.setStyleSheet(f"""
            color: {c['muted']};
            font-size: 9pt;
            font-style: italic;
        """)
        self.txt_translated.setStyleSheet(f"""
            QTextEdit {{
                background: transparent;
                border: none;
                color: {c['text']};
                font-size: 10.5pt;
                line-height: 1.4;
                selection-background-color: {ACCENT};
                selection-color: #FFFFFF;
            }}
        """)
        self.btn_copy.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT};
                border: 1px solid {ACCENT};
                border-radius: 6px;
                color: #FFFFFF;
                font-weight: 600;
                font-size: 9pt;
                padding: 5px 14px;
            }}
            QPushButton:hover {{
                background-color: #6479F0;
            }}
        """)
        self.btn_dismiss.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['card']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                color: {c['text']};
                font-size: 9pt;
                padding: 5px 14px;
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
            }}
        """)
        self.lbl_hint.setStyleSheet(f"""
            color: {c['muted']};
            font-size: 8.5pt;
        """)

    def display(self, original: str, translated: str, target: str, provider: str, pos: QPoint | None = None) -> None:
        self._apply_theme()
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if is_rtl() else Qt.LayoutDirection.LeftToRight)
        self._translated_text = translated

        target_name = LanguageService.display_name(target)
        self.lbl_lang.setText(f"🌐 {target_name}")
        self.lbl_provider.setText(provider)

        orig_clean = original.strip().replace("\r\n", " ").replace("\n", " ")
        if len(orig_clean) > 85:
            orig_clean = orig_clean[:82] + "…"
        self.lbl_orig.setText(t("popup_orig_prefix", text=orig_clean) if orig_clean else "")
        self.lbl_orig.setVisible(bool(orig_clean))

        self.txt_translated.setPlainText(translated)
        self.btn_copy.setText(t("popup_btn_copy"))
        self.btn_dismiss.setText(t("popup_btn_dismiss"))
        self.btn_dismiss.setToolTip(t("popup_tooltip_dismiss"))
        self.lbl_hint.setText(t("popup_hint"))

        self.adjustSize()
        self._position_near_cursor(pos)
        self.show()
        self.raise_()
        self.activateWindow()

        # Otomatik kapanma sayacını sıfırla ve başlat
        self._auto_close_timer.stop()
        self._auto_close_timer.setInterval(20000)
        self._auto_close_timer.start()

    def _position_near_cursor(self, preferred_pos: QPoint | None = None) -> None:
        pos = preferred_pos if preferred_pos is not None else QCursor.pos()
        screen = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry() if screen else None

        w = self.width()
        h = self.height()

        x = pos.x() + 14
        y = pos.y() + 18

        if geo:
            if x + w > geo.right() - 10:
                x = max(geo.left() + 10, pos.x() - w - 10)
            if y + h > geo.bottom() - 10:
                y = max(geo.top() + 10, pos.y() - h - 14)
            x = max(geo.left() + 10, min(x, geo.right() - w - 10))
            y = max(geo.top() + 10, min(y, geo.bottom() - h - 10))

        self.move(QPoint(x, y))

    def _copy_translation(self) -> None:
        if self._translated_text:
            QApplication.clipboard().setText(self._translated_text)
            self.btn_copy.setText(t("popup_btn_copied"))
            QTimer.singleShot(1800, lambda: self.btn_copy.setText(t("popup_btn_copy")))

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            event.accept()
        else:
            super().keyPressEvent(event)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._auto_close_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._auto_close_timer.setInterval(8000)
        self._auto_close_timer.start()
        super().leaveEvent(event)


class TranslationPopupManager(QWidget):
    """İş parçacıklarından gelen istekleri tek bir popup örneği ile yönetir."""

    def __init__(self) -> None:
        super().__init__()
        self._popup: TranslationPopup | None = None

    def show_popup(self, original: str, translated: str, target: str, provider: str, pos: QPoint | None = None) -> None:
        if self._popup is None:
            self._popup = TranslationPopup()
        self._popup.display(original, translated, target, provider, pos)
