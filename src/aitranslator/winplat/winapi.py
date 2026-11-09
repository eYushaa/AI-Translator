"""Win32 ctypes bağlamaları (yalnızca Windows). 64-bit için tüm tutamaç/işaretçi tipleri açıkça bildirilir."""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes as wt

IS_WINDOWS = sys.platform == "win32"

# ---- sabitler -------------------------------------------------------------------
VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN = 0x10, 0x11, 0x12, 0x5B, 0x5C
VK_C, VK_V = 0x43, 0x56
VK_UNASSIGNED = 0xE8  # "menü etkinleşmesini bastırma" hilesi için atanmamış tuş

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001

CF_TEXT, CF_BITMAP, CF_METAFILEPICT, CF_PALETTE, CF_UNICODETEXT, CF_ENHMETAFILE = 1, 2, 3, 9, 13, 14

GMEM_MOVEABLE = 0x0002
WM_HOTKEY, WM_QUIT, WM_APP = 0x0312, 0x0012, 0x8000
ERROR_HOTKEY_ALREADY_REGISTERED = 1409
MOD_NOREPEAT = 0x4000
GWL_STYLE = -16
ES_PASSWORD = 0x0020
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TOKEN_QUERY = 0x0008
TokenElevation = 20

ULONG_PTR = ctypes.c_size_t


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD), ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wt.LONG), ("dy", wt.LONG), ("mouseData", wt.DWORD),
        ("dwFlags", wt.DWORD), ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wt.DWORD), ("wParamL", wt.WORD), ("wParamH", wt.WORD)]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wt.DWORD), ("u", _INPUT_UNION)]


class GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.DWORD), ("flags", wt.DWORD), ("hwndActive", wt.HWND), ("hwndFocus", wt.HWND),
        ("hwndCapture", wt.HWND), ("hwndMenuOwner", wt.HWND), ("hwndMoveSize", wt.HWND),
        ("hwndCaret", wt.HWND), ("rcCaret", wt.RECT),
    ]


user32 = kernel32 = advapi32 = None  # type: ignore[assignment]

if IS_WINDOWS:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

    def _sig(func, restype, *argtypes):
        func.restype = restype
        func.argtypes = list(argtypes)

    # user32
    _sig(user32.SendInput, wt.UINT, wt.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
    _sig(user32.GetAsyncKeyState, ctypes.c_short, ctypes.c_int)
    _sig(user32.GetForegroundWindow, wt.HWND)
    _sig(user32.GetWindowThreadProcessId, wt.DWORD, wt.HWND, ctypes.POINTER(wt.DWORD))
    _sig(user32.GetGUIThreadInfo, wt.BOOL, wt.DWORD, ctypes.POINTER(GUITHREADINFO))
    _sig(user32.GetClassNameW, ctypes.c_int, wt.HWND, wt.LPWSTR, ctypes.c_int)
    _sig(user32.GetWindowLongW, wt.LONG, wt.HWND, ctypes.c_int)
    _sig(user32.IsWindow, wt.BOOL, wt.HWND)
    _sig(user32.RegisterHotKey, wt.BOOL, wt.HWND, ctypes.c_int, wt.UINT, wt.UINT)
    _sig(user32.UnregisterHotKey, wt.BOOL, wt.HWND, ctypes.c_int)
    _sig(user32.GetMessageW, wt.BOOL, ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT)
    _sig(user32.PostThreadMessageW, wt.BOOL, wt.DWORD, wt.UINT, wt.WPARAM, wt.LPARAM)
    _sig(user32.PeekMessageW, wt.BOOL, ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT, wt.UINT)
    _sig(user32.OpenClipboard, wt.BOOL, wt.HWND)
    _sig(user32.CloseClipboard, wt.BOOL)
    _sig(user32.EmptyClipboard, wt.BOOL)
    _sig(user32.EnumClipboardFormats, wt.UINT, wt.UINT)
    _sig(user32.GetClipboardData, ctypes.c_void_p, wt.UINT)
    _sig(user32.SetClipboardData, ctypes.c_void_p, wt.UINT, ctypes.c_void_p)
    _sig(user32.GetClipboardSequenceNumber, wt.DWORD)
    _sig(user32.RegisterClipboardFormatW, wt.UINT, wt.LPCWSTR)
    _sig(user32.GetClipboardFormatNameW, ctypes.c_int, wt.UINT, wt.LPWSTR, ctypes.c_int)
    # kernel32
    _sig(kernel32.GlobalAlloc, ctypes.c_void_p, wt.UINT, ctypes.c_size_t)
    _sig(kernel32.GlobalLock, ctypes.c_void_p, ctypes.c_void_p)
    _sig(kernel32.GlobalUnlock, wt.BOOL, ctypes.c_void_p)
    _sig(kernel32.GlobalSize, ctypes.c_size_t, ctypes.c_void_p)
    _sig(kernel32.GlobalFree, ctypes.c_void_p, ctypes.c_void_p)
    _sig(kernel32.OpenProcess, wt.HANDLE, wt.DWORD, wt.BOOL, wt.DWORD)
    _sig(kernel32.CloseHandle, wt.BOOL, wt.HANDLE)
    _sig(kernel32.GetCurrentProcess, wt.HANDLE)
    _sig(kernel32.GetCurrentThreadId, wt.DWORD)
    _sig(kernel32.QueryFullProcessImageNameW, wt.BOOL, wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD))
    _sig(kernel32.CreateMutexW, wt.HANDLE, ctypes.c_void_p, wt.BOOL, wt.LPCWSTR)
    # advapi32
    _sig(advapi32.OpenProcessToken, wt.BOOL, wt.HANDLE, wt.DWORD, ctypes.POINTER(wt.HANDLE))
    _sig(advapi32.GetTokenInformation, wt.BOOL, wt.HANDLE, ctypes.c_int, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD))


def require_windows() -> None:
    if not IS_WINDOWS:
        raise OSError("Bu işlev yalnızca Windows'ta çalışır.")
