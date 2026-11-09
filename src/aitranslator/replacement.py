"""TextReplacementService: çeviriyi, seçili metnin yerine (yalnızca seçimi) yazar.

Güvenlik kuralları
- Çeviri bitince pencere/odak/imleç, yakalama anındakiyle aynı değilse HİÇBİR ŞEY yazılmaz.
- Yapıştırmadan önce pano yedeklenir, sonra her durumda geri yüklenir.
- Hedef uygulama yapıştırmayı asenkron okuyabileceğinden pano, ``paste_settle`` süresi kadar beklenip geri yüklenir.
"""
from __future__ import annotations

import time
from typing import Callable

from .errors import ReplacementError
from .logging_service import get_logger
from .selection import CapturedSelection, ClipboardLike, InspectorLike, KeyboardLike

log = get_logger("replace")


def match_newlines(original: str, translated: str) -> str:
    """Özgün metin CRLF kullanıyorsa çeviriyi de CRLF'e, değilse LF'e normalleştirir."""
    norm = translated.replace("\r\n", "\n").replace("\r", "\n")
    return norm.replace("\n", "\r\n") if "\r\n" in original else norm


class TextReplacementService:
    def __init__(
        self,
        clipboard: ClipboardLike,
        keyboard: KeyboardLike,
        inspector: InspectorLike,
        sleep: Callable[[float], None] = time.sleep,
        paste_settle: float = 0.45,
    ) -> None:
        self.clipboard = clipboard
        self.keyboard = keyboard
        self.inspector = inspector
        self._sleep = sleep
        self.paste_settle = paste_settle

    def _verify_target(self, selection: CapturedSelection) -> None:
        ctx = selection.target
        now = self.inspector.foreground()
        if now is None or now.hwnd != ctx.hwnd or now.focus_hwnd != ctx.focus_hwnd:
            raise ReplacementError("Çeviri sürerken başka bir pencereye/alana geçildi; metin değiştirilmedi.")
        if ctx.caret_signature and now.caret_signature != ctx.caret_signature:
            raise ReplacementError("Çeviri sürerken imleç/seçim değişti; yanlış yere yazmamak için metin değiştirilmedi.")

    def replace(self, selection: CapturedSelection, translated: str) -> None:
        if not translated or not translated.strip():
            raise ReplacementError("Çeviri boş; metin değiştirilmedi.")
        self._verify_target(selection)
        if not self.keyboard.wait_modifiers_released(1.5):
            raise ReplacementError("Tuşlar basılı olduğu için yapıştırma iptal edildi; metin değiştirilmedi.")

        text = match_newlines(selection.text, translated)
        snapshot = self.clipboard.snapshot()
        try:
            self.clipboard.write_text(text)
            self._verify_target(selection)  # yazma ile yapıştırma arasında son kontrol
            try:
                self.keyboard.send_paste()
            except OSError as exc:
                raise ReplacementError(str(exc)) from exc
            self._sleep(self.paste_settle)
        finally:
            try:
                self.clipboard.restore(snapshot)
            except Exception:  # noqa: BLE001
                log.exception("Pano geri yüklenemedi")
        log.info("Metin değiştirildi len=%d", len(text))
