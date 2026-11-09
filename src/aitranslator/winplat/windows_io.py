"""Windows'a özgü klavye girişi ve pencere inceleme (SelectionService/ReplacementService bağımlılıkları)."""
from __future__ import annotations

import ctypes
import time
from ctypes import wintypes as wt
from dataclasses import dataclass

from . import winapi as w

# Ctrl+C'nin "kopyala" yerine "kes/kesinti (SIGINT)" anlamına gelebileceği konsol pencereleri.
UNSAFE_CLASSES = {
    "ConsoleWindowClass": "Konsol penceresi (Ctrl+C çalışan programı kesebilir)",
    "CASCADIA_HOSTING_WINDOW_CLASS": "Windows Terminal (Ctrl+C çalışan programı kesebilir)",
    "mintty": "Terminal penceresi (Ctrl+C çalışan programı kesebilir)",
    "VirtualConsoleClass": "Konsol penceresi (Ctrl+C çalışan programı kesebilir)",
}


@dataclass(frozen=True)
class TargetContext:
    hwnd: int
    focus_hwnd: int
    pid: int
    process_name: str
    window_class: str
    caret_signature: tuple
    elevated: bool = False
    password_field: bool = False


class WindowsKeyboard:
    """SendInput tabanlı klavye işlemleri."""

    def _send(self, events: list[tuple[int, bool]]) -> None:
        w.require_windows()
        arr = (w.INPUT * len(events))()
        for i, (vk, down) in enumerate(events):
            arr[i].type = w.INPUT_KEYBOARD
            arr[i].ki.wVk = vk
            arr[i].ki.wScan = w.user32.MapVirtualKeyW(vk, 0)
            arr[i].ki.dwFlags = 0 if down else w.KEYEVENTF_KEYUP
        sent = w.user32.SendInput(len(events), arr, ctypes.sizeof(w.INPUT))
        if sent != len(events):
            raise OSError("Klavye girişi gönderilemedi (hedef pencere daha yüksek yetkide olabilir).")

    def suppress_menu_activation(self) -> None:
        """Alt tuşu bırakıldığında hedef uygulamanın (özellikle Discord, Electron, Win32) menü çubuğunu açmasını ve seçimi bozmasını engeller."""
        self._send([(w.VK_CONTROL, True), (w.VK_CONTROL, False)])

    def wait_modifiers_released(self, timeout: float = 1.5) -> bool:
        keys = (w.VK_MENU, w.VK_SHIFT, w.VK_CONTROL, w.VK_LWIN, w.VK_RWIN)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not any(w.user32.GetAsyncKeyState(k) & 0x8000 for k in keys):
                return True
            time.sleep(0.01)
        return False

    def send_copy(self) -> None:
        self._send([(w.VK_CONTROL, True)])
        time.sleep(0.015)
        self._send([(w.VK_C, True)])
        time.sleep(0.015)
        self._send([(w.VK_C, False)])
        time.sleep(0.015)
        self._send([(w.VK_CONTROL, False)])

    def send_paste(self) -> None:
        self._send([(w.VK_CONTROL, True)])
        time.sleep(0.015)
        self._send([(w.VK_V, True)])
        time.sleep(0.015)
        self._send([(w.VK_V, False)])
        time.sleep(0.015)
        self._send([(w.VK_CONTROL, False)])



class WindowsInspector:
    """Ön plandaki pencere/odak/imleç bilgisi ve güvenlik denetimleri."""

    # ---- yardımcılar -------------------------------------------------------------
    @staticmethod
    def _class_name(hwnd) -> str:
        buf = ctypes.create_unicode_buffer(256)
        w.user32.GetClassNameW(hwnd, buf, 256)
        return buf.value

    @staticmethod
    def _process_name(pid: int) -> str:
        h = w.kernel32.OpenProcess(w.PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h:
            return ""
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wt.DWORD(1024)
            if w.kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                return buf.value.rsplit("\\", 1)[-1]
            return ""
        finally:
            w.kernel32.CloseHandle(h)

    @staticmethod
    def is_elevated(pid: int) -> bool:
        """Süreç yönetici yetkisinde mi? Belirlenemezse (erişim reddi) güvenli tarafta kalıp True döner."""
        h = w.kernel32.OpenProcess(w.PROCESS_QUERY_LIMITED_INFORMATION, False, pid) if pid else w.kernel32.GetCurrentProcess()
        if not h:
            return True
        token = wt.HANDLE()
        try:
            if not w.advapi32.OpenProcessToken(h, w.TOKEN_QUERY, ctypes.byref(token)):
                return True
            elev = wt.DWORD(0)
            ret = wt.DWORD(0)
            ok = w.advapi32.GetTokenInformation(token, w.TokenElevation, ctypes.byref(elev), ctypes.sizeof(elev), ctypes.byref(ret))
            return bool(elev.value) if ok else True
        finally:
            if token:
                w.kernel32.CloseHandle(token)
            if pid and h:
                w.kernel32.CloseHandle(h)

    def self_elevated(self) -> bool:
        return self.is_elevated(0)

    # ---- API -----------------------------------------------------------------------
    def foreground(self) -> TargetContext | None:
        w.require_windows()
        hwnd = w.user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = wt.DWORD(0)
        tid = w.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        info = w.GUITHREADINFO()
        info.cbSize = ctypes.sizeof(w.GUITHREADINFO)
        focus = hwnd
        caret: tuple = ()
        if w.user32.GetGUIThreadInfo(tid, ctypes.byref(info)):
            focus = info.hwndFocus or hwnd
            if info.hwndCaret:
                r = info.rcCaret
                caret = (int(info.hwndCaret), r.left, r.top, r.right, r.bottom)
        focus_class = self._class_name(focus)
        password = False
        if focus_class.lower() == "edit":
            password = bool(w.user32.GetWindowLongW(focus, w.GWL_STYLE) & w.ES_PASSWORD)
        return TargetContext(
            hwnd=int(hwnd),
            focus_hwnd=int(focus),
            pid=int(pid.value),
            process_name=self._process_name(int(pid.value)),
            window_class=self._class_name(hwnd),
            caret_signature=caret,
            elevated=self.is_elevated(int(pid.value)),
            password_field=password,
        )

    def unsupported_reason(self, ctx: TargetContext) -> str | None:
        """Bu pencerede güvenle çalışılamıyorsa kullanıcıya gösterilecek açıklama, aksi hâlde None."""
        if ctx.window_class in UNSAFE_CLASSES:
            return f"Bu pencere desteklenmiyor: {UNSAFE_CLASSES[ctx.window_class]}."
        if ctx.password_field:
            return "Parola alanlarında çeviri yapılmaz."
        if ctx.elevated and not self.self_elevated():
            return (
                "Hedef uygulama yönetici yetkisiyle çalışıyor; Windows buna giriş göndermeyi engeller. "
                "Çeviri uygulamasını da yönetici olarak çalıştırın."
            )
        return None
