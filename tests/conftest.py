"""Test yardımcıları: Windows'a ihtiyaç duymadan masaüstü davranışını taklit eden sahte nesneler."""
from __future__ import annotations

import copy

import httpx
import pytest

from aitranslator.secure_storage import MemoryBackend, SecureStorage
from aitranslator.settings import SettingsManager
from aitranslator.winplat.windows_io import TargetContext


class FakeClipboard:
    """Çok biçimli pano taklidi. data: {biçim: bayt/metin}."""

    def __init__(self, data=None):
        self.data = dict(data or {})
        self.seq = 1
        self.fail_write = False

    def sequence_number(self):
        return self.seq

    def snapshot(self):
        class Snap:
            lossy = False

        s = Snap()
        s.data = copy.deepcopy(self.data)
        return s

    def restore(self, snap):
        self.data = copy.deepcopy(snap.data)
        self.seq += 1

    def read_text(self):
        return self.data.get("text")

    def write_text(self, text, hide_from_history=True):
        if self.fail_write:
            raise OSError("pano kilitli")
        self.data = {"text": text}
        self.seq += 1


class FakeDesktop:
    """Tek bir metin alanı + pano + klavye + pencere denetçisi."""

    def __init__(self, text="Merhaba dünya. Bu bir testtir.", sel=(0, 13), process="notepad.exe", clipboard=None):
        self.text = text
        self.sel = list(sel)
        self.clipboard = clipboard or FakeClipboard({"text": "ESKİ PANO", "html": "<b>eski</b>", "image": b"\x89PNG"})
        self.ctx = TargetContext(hwnd=100, focus_hwnd=101, pid=1, process_name=process, window_class="Notepad", caret_signature=(101, 5, 5, 6, 20))
        self.unsupported = None
        self.modifiers_stuck = False
        self.events: list[str] = []
        self.on_before_paste = None  # test kancası (ör. odak değiştirme)

    # --- klavye ---
    def suppress_menu_activation(self):
        self.events.append("suppress")

    def wait_modifiers_released(self, timeout=1.5):
        return not self.modifiers_stuck

    def send_copy(self):
        self.events.append("copy")
        a, b = self.sel
        if a != b:
            self.clipboard.write_text(self.text[a:b])

    def send_paste(self):
        self.events.append("paste")
        if self.on_before_paste:
            self.on_before_paste()
        a, b = self.sel
        pasted = self.clipboard.read_text() or ""
        self.text = self.text[:a] + pasted + self.text[b:]
        self.sel = [a, a + len(pasted)]

    # --- denetçi ---
    def foreground(self):
        return self.ctx

    def unsupported_reason(self, ctx):
        return self.unsupported


@pytest.fixture
def desktop():
    return FakeDesktop()


@pytest.fixture
def settings(tmp_path):
    return SettingsManager(tmp_path / "settings.json")


@pytest.fixture
def secrets():
    return SecureStorage(MemoryBackend())


def mock_transport(handler):
    return httpx.MockTransport(handler)
