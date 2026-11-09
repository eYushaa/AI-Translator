"""Sade, modern, Windows 11'e yakın görünüm: Fusion + özel QSS (açık/koyu tema sistemi izler)."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QApplication

ACCENT = "#4F6BED"

_LIGHT = {"bg": "#F3F4F8", "card": "#FFFFFF", "text": "#1B1D26", "muted": "#6B7080", "border": "#E1E4EC", "hover": "#E9ECFA", "input": "#FFFFFF"}
_DARK = {"bg": "#16181F", "card": "#1F222C", "text": "#ECEEF6", "muted": "#9AA0B4", "border": "#2E3240", "hover": "#2A2F44", "input": "#262A36"}


def is_dark() -> bool:
    try:
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:  # eski Qt
        return False


def stylesheet() -> str:
    c = _DARK if is_dark() else _LIGHT
    return f"""
    * {{ font-family: "Segoe UI Variable", "Segoe UI", sans-serif; font-size: 10pt; color: {c['text']}; }}
    QMainWindow, QDialog, #Root {{ background: {c['bg']}; }}
    #LeftPanel {{ background: {c['card']}; border: none; border-right: 1px solid {c['border']}; border-left: 1px solid {c['border']}; }}
    #Sidebar {{ background: transparent; border: none; padding: 10px 6px; outline: 0; }}
    #Sidebar::item {{ padding: 10px 14px; margin: 2px 4px; border-radius: 8px; }}
    #Sidebar::item:hover {{ background: {c['hover']}; }}
    #Sidebar::item:selected {{ background: {ACCENT}; color: white; }}
    #SidebarBottom {{ background: transparent; border-top: 1px solid {c['border']}; padding: 12px 12px 16px 12px; }}
    #Card {{ background: {c['card']}; border: 1px solid {c['border']}; border-radius: 12px; }}
    #Title {{ font-size: 17pt; font-weight: 600; }}
    #Subtle, QLabel[muted="true"] {{ color: {c['muted']}; }}
    #Warn {{ color: #C77700; }}
    #Ok {{ color: #1E8E5A; }}
    #Err {{ color: #D13438; }}
    QLineEdit, QComboBox, QKeySequenceEdit, QSpinBox, QTableWidget, QPlainTextEdit, QTextEdit {{
        background: {c['input']}; border: 1px solid {c['border']}; border-radius: 8px; padding: 6px 8px; selection-background-color: {ACCENT};
    }}
    QLineEdit:focus, QComboBox:focus, QKeySequenceEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{ border: 1px solid {ACCENT}; }}

    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox QAbstractItemView {{ background: {c['card']}; border: 1px solid {c['border']}; selection-background-color: {ACCENT}; selection-color: white; }}
    QPushButton {{ background: {c['card']}; border: 1px solid {c['border']}; border-radius: 8px; padding: 7px 16px; }}
    QPushButton:hover {{ background: {c['hover']}; }}
    QPushButton#Primary {{ background: {ACCENT}; border: 1px solid {ACCENT}; color: white; font-weight: 600; }}
    QPushButton#Primary:hover {{ background: #6479F0; }}
    QCheckBox {{ spacing: 8px; padding: 3px 0; }}
    QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 1px solid {c['border']}; background: {c['input']}; }}
    QCheckBox::indicator:checked {{ background: {ACCENT}; border: 1px solid {ACCENT}; }}
    QTabWidget::pane {{ border: none; }}
    QTabBar::tab {{ padding: 8px 16px; margin-right: 4px; border-radius: 8px; background: transparent; }}
    QTabBar::tab:selected {{ background: {c['hover']}; font-weight: 600; }}
    QHeaderView::section {{ background: {c['card']}; border: none; border-bottom: 1px solid {c['border']}; padding: 6px; }}
    QScrollArea {{ border: none; background: transparent; }}
    QMenu {{ background: {c['card']}; border: 1px solid {c['border']}; border-radius: 8px; padding: 6px; }}
    QMenu::item {{ padding: 7px 22px; border-radius: 6px; }}
    QMenu::item:selected {{ background: {ACCENT}; color: white; }}
    """


def make_app_icon(size: int = 256) -> QIcon:
    """Uygulama simgesi kod ile çizilir (ikili varlık dosyası gerekmez)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0, QColor("#6A82FB"))
    grad.setColorAt(1, QColor("#3A4FD4"))
    path = QPainterPath()
    path.addRoundedRect(QRectF(size * 0.06, size * 0.06, size * 0.88, size * 0.88), size * 0.22, size * 0.22)
    p.fillPath(path, grad)
    p.setPen(QColor("white"))
    f = QFont("Segoe UI", int(size * 0.30), QFont.Weight.Bold)
    p.setFont(f)
    p.drawText(QRectF(0, size * 0.10, size, size * 0.55), Qt.AlignmentFlag.AlignCenter, "A文")
    pen = QPen(QColor("white"), size * 0.035, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    y = size * 0.76
    p.drawLine(int(size * 0.28), int(y), int(size * 0.72), int(y))
    p.drawLine(int(size * 0.62), int(y - size * 0.06), int(size * 0.72), int(y))
    p.drawLine(int(size * 0.62), int(y + size * 0.06), int(size * 0.72), int(y))
    p.end()
    return QIcon(pm)


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(stylesheet())
