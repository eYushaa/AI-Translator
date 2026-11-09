"""ClipboardManager (Windows): pano durumunu yakalar, geçici metin yazar ve eski içeriği geri yükler.

Tasarım notları
- Tüm HGLOBAL tabanlı biçimler (metin, HTML, RTF, DIB, dosya listesi …) ham bayt olarak saklanır.
- GDI tutamaçları (CF_BITMAP, CF_PALETTE, metafile) ve OLE nesne biçimleri kopyalanamaz; Windows zaten
  CF_BITMAP'i CF_DIB'den üretir. Kopyalanamayan biçim varsa ``lossy=True`` işaretlenir.
- Geçici metin yazılırken "geçmişe ekleme / bulut eşitleme" dışlama biçimleri eklenir; böylece Win+V
  geçmişinde çeviri ara metinleri birikmez.
"""
from __future__ import annotations

import ctypes
import struct
import time
from dataclasses import dataclass, field

from ..logging_service import get_logger
from . import winapi as w

log = get_logger("clipboard")

MAX_SNAPSHOT_BYTES = 64 * 1024 * 1024
_SKIP_FORMATS = {w.CF_BITMAP, w.CF_METAFILEPICT, w.CF_PALETTE, w.CF_ENHMETAFILE}
_SKIP_NAMES = {"DataObject", "Embed Source", "Link Source", "Embedded Object", "Object Descriptor", "Link Source Descriptor"}


class ClipboardError(Exception):
    pass


@dataclass
class ClipboardSnapshot:
    items: list[tuple[int, bytes]] = field(default_factory=list)
    lossy: bool = False

    @property
    def empty(self) -> bool:
        return not self.items


class ClipboardManager:
    OPEN_RETRIES = 25
    OPEN_DELAY = 0.02

    # ---- düşük seviye -------------------------------------------------------------
    def _open(self) -> None:
        w.require_windows()
        for _ in range(self.OPEN_RETRIES):
            if w.user32.OpenClipboard(None):
                return
            time.sleep(self.OPEN_DELAY)
        raise ClipboardError("Pano başka bir uygulama tarafından kullanılıyor.")

    @staticmethod
    def _close() -> None:
        w.user32.CloseClipboard()

    @staticmethod
    def _format_name(fmt: int) -> str:
        buf = ctypes.create_unicode_buffer(256)
        n = w.user32.GetClipboardFormatNameW(fmt, buf, 256)
        return buf.value if n > 0 else ""

    @staticmethod
    def _alloc(data: bytes):
        h = w.kernel32.GlobalAlloc(w.GMEM_MOVEABLE, max(len(data), 1))
        if not h:
            raise ClipboardError("Bellek ayrılamadı.")
        ptr = w.kernel32.GlobalLock(h)
        if not ptr:
            w.kernel32.GlobalFree(h)
            raise ClipboardError("Bellek kilitlenemedi.")
        ctypes.memmove(ptr, data, len(data))
        w.kernel32.GlobalUnlock(h)
        return h

    def _set_bytes(self, fmt: int, data: bytes) -> bool:
        h = self._alloc(data)
        if not w.user32.SetClipboardData(fmt, h):
            w.kernel32.GlobalFree(h)  # sahiplik sistemde değil → biz serbest bırakırız
            return False
        return True

    # ---- genel API ----------------------------------------------------------------
    def sequence_number(self) -> int:
        w.require_windows()
        return int(w.user32.GetClipboardSequenceNumber())

    def snapshot(self) -> ClipboardSnapshot:
        snap = ClipboardSnapshot()
        total = 0
        self._open()
        try:
            fmt = 0
            while True:
                fmt = w.user32.EnumClipboardFormats(fmt)
                if not fmt:
                    break
                if fmt in _SKIP_FORMATS or 0x0300 <= fmt <= 0x03FF or 0x0080 <= fmt <= 0x008E:
                    snap.lossy = True
                    continue
                if fmt >= 0xC000 and self._format_name(fmt) in _SKIP_NAMES:
                    snap.lossy = True
                    continue
                handle = w.user32.GetClipboardData(fmt)
                if not handle:
                    snap.lossy = True
                    continue
                size = w.kernel32.GlobalSize(handle)
                if size == 0:
                    snap.lossy = True
                    continue
                total += size
                if total > MAX_SNAPSHOT_BYTES:
                    snap.lossy = True
                    break
                ptr = w.kernel32.GlobalLock(handle)
                if not ptr:
                    snap.lossy = True
                    continue
                try:
                    snap.items.append((fmt, ctypes.string_at(ptr, size)))
                finally:
                    w.kernel32.GlobalUnlock(handle)
        finally:
            self._close()
        return snap

    def restore(self, snap: ClipboardSnapshot) -> None:
        self._open()
        try:
            w.user32.EmptyClipboard()
            for fmt, data in snap.items:
                if not self._set_bytes(fmt, data):
                    log.warning("Pano biçimi geri yüklenemedi: %s", fmt)
        finally:
            self._close()

    def read_text(self) -> str | None:
        self._open()
        try:
            handle = w.user32.GetClipboardData(w.CF_UNICODETEXT)
            if not handle:
                return None
            ptr = w.kernel32.GlobalLock(handle)
            if not ptr:
                return None
            try:
                return ctypes.wstring_at(ptr)
            finally:
                w.kernel32.GlobalUnlock(handle)
        finally:
            self._close()

    def write_text(self, text: str, hide_from_history: bool = True) -> None:
        data = (text + "\0").encode("utf-16-le")
        self._open()
        try:
            w.user32.EmptyClipboard()
            if not self._set_bytes(w.CF_UNICODETEXT, data):
                raise ClipboardError("Panoya metin yazılamadı.")
            if hide_from_history:
                zero = struct.pack("<I", 0)
                for name in (
                    "ExcludeClipboardContentFromMonitorProcessing",
                    "CanIncludeInClipboardHistory",
                    "CanUploadToCloudClipboard",
                ):
                    fid = w.user32.RegisterClipboardFormatW(name)
                    if fid:
                        self._set_bytes(fid, zero)
        finally:
            self._close()
