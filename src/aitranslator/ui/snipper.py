"""Ekran Alıntısı (Screen Snipper) Aracı: Kullanıcının ekrandan istediği alanı seçip OCR yapmasını sağlar."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QGuiApplication, QKeyEvent, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from ..i18n import t
from .theme import ACCENT


class ScreenSnipperOverlay(QWidget):
    snippet_captured = Signal(object, object)  # (QImage, QPoint)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._pixmap: QPixmap | None = None
        self._start_pos: QPoint | None = None
        self._current_pos: QPoint | None = None
        self._is_selecting = False
        self._virtual_rect = QRect()

    def start_capture(self) -> None:
        """Tüm monitörlerin ekran görüntüsünü alır ve tam ekran seçim örtüsünü açar."""
        screens = QGuiApplication.screens()
        if not screens:
            return

        total_rect = QRect()
        for s in screens:
            total_rect = total_rect.united(s.geometry())
        self._virtual_rect = total_rect

        # Tüm monitörleri birleşik bir pixmap'e aktar
        full_pixmap = QPixmap(total_rect.size())
        full_pixmap.fill(Qt.GlobalColor.black)
        painter = QPainter(full_pixmap)
        for s in screens:
            pm = s.grabWindow(0)
            painter.drawPixmap(s.geometry().topLeft() - total_rect.topLeft(), pm)
        painter.end()

        self._pixmap = full_pixmap
        self._start_pos = None
        self._current_pos = None
        self._is_selecting = False

        self.setGeometry(total_rect)
        self.show()
        self.raise_()
        self.activateWindow()

        # Windows'ta odağı garanti et
        try:
            import ctypes
            ctypes.windll.user32.SetForegroundWindow(int(self.winId()))
        except Exception:
            pass

    def paintEvent(self, event) -> None:  # noqa: N802
        if not self._pixmap:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # 1. Tam ekran görüntüyü çiz
        painter.drawPixmap(0, 0, self._pixmap)

        # 2. Karartma katmanı (dimmed overlay)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 115))

        # 3. Seçilen alan varsa karartmayı kaldır ve vurgula
        if self._start_pos and self._current_pos:
            selection = QRect(self._start_pos, self._current_pos).normalized()
            if selection.width() > 2 and selection.height() > 2:
                # Orijinal görüntüyü seçilen alana aydınlık çiz
                painter.drawPixmap(selection, self._pixmap, selection)

                # Seçim çerçevesi (Accent rengi)
                pen = QPen(QColor(ACCENT), 2)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(selection)

                # Köşe vurguları (Corner accents)
                corner_len = min(12, min(selection.width(), selection.height()) // 3)
                pen_corner = QPen(QColor("#FFFFFF"), 3)
                painter.setPen(pen_corner)
                # Sol-üst
                painter.drawLine(selection.left(), selection.top(), selection.left() + corner_len, selection.top())
                painter.drawLine(selection.left(), selection.top(), selection.left(), selection.top() + corner_len)
                # Sağ-üst
                painter.drawLine(selection.right(), selection.top(), selection.right() - corner_len, selection.top())
                painter.drawLine(selection.right(), selection.top(), selection.right(), selection.top() + corner_len)
                # Sol-alt
                painter.drawLine(selection.left(), selection.bottom(), selection.left() + corner_len, selection.bottom())
                painter.drawLine(selection.left(), selection.bottom(), selection.left(), selection.bottom() - corner_len)
                # Sağ-alt
                painter.drawLine(selection.right(), selection.bottom(), selection.right() - corner_len, selection.bottom())
                painter.drawLine(selection.right(), selection.bottom(), selection.right(), selection.bottom() - corner_len)

                # Boyut rozeti (Örn: "420 × 160 px")
                badge_text = f"{selection.width()} × {selection.height()} px"
                font = QFont("Segoe UI", 9)
                font.setBold(True)
                painter.setFont(font)

                badge_w, badge_h = 100, 22
                badge_x = selection.left()
                badge_y = selection.bottom() + 6
                if badge_y + badge_h > self.height() - 10:
                    badge_y = selection.top() - badge_h - 6

                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(0, 0, 0, 180))
                painter.drawRoundedRect(QRect(badge_x, badge_y, badge_w, badge_h), 5, 5)

                painter.setPen(QColor("#FFFFFF"))
                painter.drawText(QRect(badge_x, badge_y, badge_w, badge_h), Qt.AlignmentFlag.AlignCenter, badge_text)

        # 4. Üst ortada şık bilgilendirme rozeti
        cursor_pos = QCursor.pos()
        screen = QGuiApplication.screenAt(cursor_pos) or QGuiApplication.primaryScreen()
        scr_geo = screen.geometry() if screen else self.rect()

        info_text = t("ocr_snip_instruction")
        info_font = QFont("Segoe UI", 10)
        info_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(info_font)

        pill_w = max(320, len(info_text) * 9 + 40)
        pill_h = 36
        pill_x = scr_geo.left() - self._virtual_rect.left() + (scr_geo.width() - pill_w) // 2
        pill_y = scr_geo.top() - self._virtual_rect.top() + 24

        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.setBrush(QColor(20, 24, 33, 210))
        painter.drawRoundedRect(QRect(pill_x, pill_y, pill_w, pill_h), 18, 18)

        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(QRect(pill_x, pill_y, pill_w, pill_h), Qt.AlignmentFlag.AlignCenter, info_text)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_pos = event.position().toPoint()
            self._current_pos = self._start_pos
            self._is_selecting = True
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            self.close()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._is_selecting:
            self._current_pos = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._is_selecting:
            self._is_selecting = False
            self._current_pos = event.position().toPoint()
            self.hide()

            if self._start_pos and self._current_pos and self._pixmap:
                rect = QRect(self._start_pos, self._current_pos).normalized()
                if rect.width() >= 8 and rect.height() >= 8:
                    cropped = self._pixmap.copy(rect).toImage()
                    # Popup konumu: seçimin sağ alt köşesi (ekran sınırlarını aşmayacak şekilde)
                    global_bottom_right = self.mapToGlobal(rect.bottomRight())
                    self.snippet_captured.emit(cropped, global_bottom_right)
            self.close()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            event.accept()
        else:
            super().keyPressEvent(event)


class ScreenSnipperManager:
    """Tekil snipper aracı örneğini yönetir."""

    def __init__(self, on_snippet_captured: Callable[[object, object], None]) -> None:
        self._on_captured = on_snippet_captured
        self._snipper: ScreenSnipperOverlay | None = None

    def start_snip(self) -> None:
        if self._snipper is None:
            self._snipper = ScreenSnipperOverlay()
            self._snipper.snippet_captured.connect(self._on_captured)
        self._snipper.start_capture()

