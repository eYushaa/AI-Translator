"""TextSelectionService: kısayol anında seçili metni güvenilir ve kayıpsız biçimde alır.

Yöntem: Ctrl+C simülasyonu + pano. Adımlar
1. Hedef pencereyi/odağı kaydet ve güvensiz hedefleri (konsol, parola alanı, yönetici penceresi) reddet.
2. Pano içeriğini yedekle, panoya benzersiz bir "nöbetçi" metin yaz, Ctrl+C gönder.
3. Pano sıra numarası değişip nöbetçiden farklı metin geldiyse bu seçili metindir.
4. Panoyu HER DURUMDA (hata dahil) eski hâline döndür.

Seçim yoksa tüm alan ASLA seçilip silinmez; kullanıcıya "önce metin seçin" bildirimi gösterilir.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Callable, Protocol

from .errors import SelectionError
from .logging_service import get_logger

log = get_logger("selection")

#: Seçim yokken Ctrl+C ile "geçerli satırı" kopyalayan düzenleyiciler (satır sonu ile biten metin → seçim yok say)
LINE_COPY_EDITORS = {"code.exe", "cursor.exe", "devenv.exe", "sublime_text.exe", "idea64.exe", "pycharm64.exe", "rider64.exe", "webstorm64.exe"}


class ClipboardLike(Protocol):
    def snapshot(self): ...
    def restore(self, snap) -> None: ...
    def read_text(self) -> str | None: ...
    def write_text(self, text: str, hide_from_history: bool = True) -> None: ...
    def sequence_number(self) -> int: ...


class KeyboardLike(Protocol):
    def suppress_menu_activation(self) -> None: ...
    def wait_modifiers_released(self, timeout: float = 1.5) -> bool: ...
    def send_copy(self) -> None: ...
    def send_paste(self) -> None: ...


class InspectorLike(Protocol):
    def foreground(self): ...
    def unsupported_reason(self, ctx) -> str | None: ...


@dataclass
class CapturedSelection:
    text: str
    target: object  # winplat.windows_io.TargetContext


class TextSelectionService:
    def __init__(
        self,
        clipboard: ClipboardLike,
        keyboard: KeyboardLike,
        inspector: InspectorLike,
        sleep: Callable[[float], None] = time.sleep,
        copy_timeout: float = 1.0,
        poll_interval: float = 0.02,
    ) -> None:
        self.clipboard = clipboard
        self.keyboard = keyboard
        self.inspector = inspector
        self._sleep = sleep
        self.copy_timeout = copy_timeout
        self.poll_interval = poll_interval

    def capture(self) -> CapturedSelection:
        # Alt basılıyken menü çubuğunun etkinleşmesini engelle (bkz. WindowsKeyboard)
        try:
            self.keyboard.suppress_menu_activation()
        except OSError:
            pass  # hedef yüksek yetkideyse aşağıdaki denetim bunu anlaşılır şekilde bildirir

        ctx = self.inspector.foreground()
        if ctx is None:
            raise SelectionError("Etkin bir pencere bulunamadı.")
        reason = self.inspector.unsupported_reason(ctx)
        if reason:
            raise SelectionError(reason)
        if not self.keyboard.wait_modifiers_released():
            raise SelectionError("Kısayol tuşlarını bırakıp işlemi tekrar deneyin.")
        # Tuşlar bırakıldıktan sonra Alt kaynaklı menü etkinleşmesini tekrar bastır
        try:
            self.keyboard.suppress_menu_activation()
        except OSError:
            pass

        snapshot = self.clipboard.snapshot()
        if getattr(snapshot, "lossy", False):
            log.warning("Pano yedeği kısmi: bazı özel biçimler geri yüklenemeyebilir")
        text: str | None = None
        try:
            sentinel = f"⁠AITR-{uuid.uuid4().hex}⁠"
            self.clipboard.write_text(sentinel)
            seq0 = self.clipboard.sequence_number()
            try:
                self.keyboard.send_copy()
            except OSError as exc:
                raise SelectionError(str(exc)) from exc
            deadline = time.monotonic() + self.copy_timeout
            retried = False
            while time.monotonic() < deadline:
                self._sleep(self.poll_interval)
                if self.clipboard.sequence_number() == seq0:
                    if not retried and (time.monotonic() - (deadline - self.copy_timeout)) > 0.25:
                        retried = True
                        try:
                            self.keyboard.send_copy()
                        except Exception:
                            pass
                    continue
                got = self.clipboard.read_text()
                if got and got != sentinel:
                    text = got
                    break
        finally:
            try:
                self.clipboard.restore(snapshot)
            except Exception:  # noqa: BLE001
                log.exception("Pano geri yüklenemedi")

        if not text or not text.strip():
            raise SelectionError("Seçili metin bulunamadı. Önce çevirmek istediğiniz metni seçin.")
        if ctx.process_name.lower() in LINE_COPY_EDITORS and text.endswith(("\n", "\r")) and text.strip().count("\n") == 0:
            # Bu düzenleyiciler seçim yokken satırı kopyalar → gerçek bir seçim olmadığını varsay
            raise SelectionError("Seçili metin bulunamadı. Önce çevirmek istediğiniz metni seçin.")

        after = self.inspector.foreground()
        if after is None or after.hwnd != ctx.hwnd:
            raise SelectionError("Metin alınırken pencere değişti; işlem iptal edildi.")
        log.info("Seçim alındı len=%d app=%s", len(text), ctx.process_name)
        return CapturedSelection(text=text, target=ctx)
