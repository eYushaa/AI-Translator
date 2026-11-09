"""HotkeyManager: Windows genelinde RegisterHotKey tabanlı kısayollar.

RegisterHotKey iş parçacığına bağlıdır; bu yüzden kısayollar kendi mesaj döngüsü olan özel bir iş parçacığında
kaydedilir. Ayarlar değişince ``apply`` iş parçacığını yeniden başlatır ve kayıt sonuçlarını (çakışma dahil) döner.
"""
from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes as wt
from typing import Callable

from ..logging_service import get_logger
from . import winapi as w
from .hotkey_parse import Hotkey, HotkeyParseError, find_duplicates, parse_hotkey

log = get_logger("hotkeys")


class HotkeyManager:
    def __init__(self, on_hotkey: Callable[[str], None]) -> None:
        self._on_hotkey = on_hotkey
        self._thread: threading.Thread | None = None
        self._thread_id = 0
        self._results: dict[str, str | None] = {}

    # ---- genel API ------------------------------------------------------------------
    def apply(self, bindings: dict[str, str], enabled: bool = True) -> dict[str, str | None]:
        """``bindings``: {ad: "Alt+B"}. Dönüş: {ad: None (başarılı) | hata mesajı}."""
        self.stop()
        if not enabled:
            return {name: None for name in bindings}
        results: dict[str, str | None] = dict(find_duplicates(bindings))
        parsed: dict[str, Hotkey] = {}
        for name, text in bindings.items():
            if name in results:
                continue
            try:
                parsed[name] = parse_hotkey(text)
            except HotkeyParseError as exc:
                results[name] = str(exc)
        if parsed:
            results.update(self._start(parsed))
        for name in bindings:
            results.setdefault(name, None)
        self._results = results
        return results

    def stop(self) -> None:
        thread, tid = self._thread, self._thread_id
        if thread and thread.is_alive() and tid:
            w.user32.PostThreadMessageW(tid, w.WM_QUIT, 0, 0)
            thread.join(timeout=2)
        self._thread = None
        self._thread_id = 0

    # ---- iş parçacığı ---------------------------------------------------------------
    def _start(self, parsed: dict[str, Hotkey]) -> dict[str, str | None]:
        w.require_windows()
        ready = threading.Event()
        out: dict[str, str | None] = {}
        holder: dict[str, int] = {}

        def run() -> None:
            holder["tid"] = w.kernel32.GetCurrentThreadId()
            msg = wt.MSG()
            w.user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)  # mesaj kuyruğunu oluştur
            ids: dict[int, str] = {}
            for i, (name, hk) in enumerate(parsed.items(), start=1):
                if w.user32.RegisterHotKey(None, i, hk.modifiers | w.MOD_NOREPEAT, hk.vk):
                    ids[i] = name
                    out[name] = None
                else:
                    err = ctypes.get_last_error()
                    if err == w.ERROR_HOTKEY_ALREADY_REGISTERED:
                        out[name] = f"'{hk.normalized()}' kısayolu başka bir uygulama tarafından kullanılıyor."
                    else:
                        out[name] = f"'{hk.normalized()}' kısayolu kaydedilemedi (hata {err})."
            ready.set()
            try:
                while w.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                    if msg.message == w.WM_HOTKEY:
                        name = ids.get(int(msg.wParam))
                        if name:
                            try:
                                self._on_hotkey(name)
                            except Exception:  # noqa: BLE001 - mesaj döngüsü asla ölmemeli
                                log.exception("Kısayol işleyicisi hata verdi")
            finally:
                for i in ids:
                    w.user32.UnregisterHotKey(None, i)

        self._thread = threading.Thread(target=run, name="HotkeyLoop", daemon=True)
        self._thread.start()
        if not ready.wait(timeout=3):
            log.error("Kısayol iş parçacığı başlatılamadı")
            return {name: "Kısayol servisi başlatılamadı." for name in parsed}
        self._thread_id = holder.get("tid", 0)
        return out
