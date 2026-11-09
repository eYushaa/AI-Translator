"""Kısayol metni ("Alt+B") ayrıştırma. Platformdan bağımsızdır (test edilebilir)."""
from __future__ import annotations

from dataclasses import dataclass

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

_MOD_NAMES = {
    "alt": MOD_ALT,
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "strg": MOD_CONTROL,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "meta": MOD_WIN,
    "super": MOD_WIN,
}

_NAMED_KEYS = {
    "space": 0x20, "enter": 0x0D, "return": 0x0D, "tab": 0x09, "esc": 0x1B, "escape": 0x1B,
    "backspace": 0x08, "delete": 0x2E, "del": 0x2E, "insert": 0x2D, "ins": 0x2D,
    "home": 0x24, "end": 0x23, "pageup": 0x21, "pgup": 0x21, "pagedown": 0x22, "pgdn": 0x22,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
}


class HotkeyParseError(ValueError):
    pass


@dataclass(frozen=True)
class Hotkey:
    modifiers: int
    vk: int

    def normalized(self) -> str:
        parts = []
        if self.modifiers & MOD_CONTROL:
            parts.append("Ctrl")
        if self.modifiers & MOD_ALT:
            parts.append("Alt")
        if self.modifiers & MOD_SHIFT:
            parts.append("Shift")
        if self.modifiers & MOD_WIN:
            parts.append("Win")
        parts.append(_vk_name(self.vk))
        return "+".join(parts)


def _vk_name(vk: int) -> str:
    if 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A:
        return chr(vk)
    if 0x70 <= vk <= 0x87:
        return f"F{vk - 0x6F}"
    for name, code in _NAMED_KEYS.items():
        if code == vk and len(name) > 2:
            return name.capitalize()
    return f"0x{vk:02X}"


def parse_hotkey(text: str) -> Hotkey:
    """'Alt+B', 'ctrl+shift+F5' gibi metni (değiştirici bayrakları, sanal tuş kodu) çiftine çevirir."""
    if not text or not text.strip():
        raise HotkeyParseError("Kısayol boş.")
    mods = 0
    vk: int | None = None
    for raw in text.split("+"):
        token = raw.strip()
        low = token.lower()
        if not token:
            raise HotkeyParseError(f"Geçersiz kısayol: '{text}'")
        if low in _MOD_NAMES:
            mods |= _MOD_NAMES[low]
            continue
        if vk is not None:
            raise HotkeyParseError("Kısayolda yalnızca bir ana tuş olabilir.")
        if len(token) == 1 and token.isascii() and token.isalnum():
            vk = ord(token.upper())
        elif low.startswith("f") and low[1:].isdigit() and 1 <= int(low[1:]) <= 24:
            vk = 0x70 + int(low[1:]) - 1
        elif low in _NAMED_KEYS:
            vk = _NAMED_KEYS[low]
        else:
            raise HotkeyParseError(f"Tanınmayan tuş: '{token}'")
    if vk is None:
        raise HotkeyParseError("Kısayolda bir ana tuş (ör. B) bulunmalı.")
    if mods == 0:
        raise HotkeyParseError("Kısayol en az bir değiştirici tuş (Alt, Ctrl, Shift, Win) içermeli.")
    return Hotkey(mods, vk)


def find_duplicates(bindings: dict[str, str]) -> dict[str, str]:
    """Aynı tuş kombinasyonuna atanmış birden fazla işlev varsa {işlev: hata mesajı} döner."""
    seen: dict[Hotkey, str] = {}
    errors: dict[str, str] = {}
    for name, text in bindings.items():
        try:
            hk = parse_hotkey(text)
        except HotkeyParseError as exc:
            errors[name] = str(exc)
            continue
        if hk in seen:
            errors[name] = f"'{text}' kısayolu '{seen[hk]}' ile çakışıyor."
        else:
            seen[hk] = name
    return errors
