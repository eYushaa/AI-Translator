import pytest

from aitranslator.errors import ReplacementError, SelectionError
from aitranslator.replacement import TextReplacementService, match_newlines
from aitranslator.selection import TextSelectionService
from aitranslator.winplat.windows_io import TargetContext


def services(d):
    sel = TextSelectionService(d.clipboard, d, d, sleep=lambda s: None, copy_timeout=0.2)
    rep = TextReplacementService(d.clipboard, d, d, sleep=lambda s: None)
    return sel, rep


def test_capture_returns_selection_and_restores_clipboard(desktop):
    sel, _ = services(desktop)
    before = dict(desktop.clipboard.data)
    cap = sel.capture()
    assert cap.text == "Merhaba dünya"
    assert desktop.clipboard.data == before  # pano (metin + html + resim) eksiksiz geri geldi
    assert "suppress" in desktop.events  # Alt menüsü bastırıldı


def test_replace_only_selection_rest_of_field_preserved(desktop):
    sel, rep = services(desktop)
    cap = sel.capture()
    rep.replace(cap, "Hello world")
    assert desktop.text == "Hello world. Bu bir testtir."
    assert desktop.clipboard.data["text"] == "ESKİ PANO" and desktop.clipboard.data["html"] == "<b>eski</b>"


def test_no_selection_never_touches_field(desktop):
    desktop.sel = [5, 5]
    sel, _ = services(desktop)
    original = desktop.text
    with pytest.raises(SelectionError) as ei:
        sel.capture()
    assert "seçin" in ei.value.message.lower()
    assert desktop.text == original
    assert desktop.clipboard.data["text"] == "ESKİ PANO"
    assert "paste" not in desktop.events


def test_unsupported_target_reported(desktop):
    desktop.unsupported = "Parola alanlarında çeviri yapılmaz."
    sel, _ = services(desktop)
    with pytest.raises(SelectionError) as ei:
        sel.capture()
    assert "Parola" in ei.value.message
    assert "copy" not in desktop.events  # unsupported alanda Ctrl+C bile gönderilmez


def test_keys_still_held_aborts(desktop):
    desktop.modifiers_stuck = True
    sel, _ = services(desktop)
    with pytest.raises(SelectionError):
        sel.capture()
    assert "copy" not in desktop.events


def test_line_copy_editor_without_selection_is_rejected():
    from conftest import FakeDesktop

    d = FakeDesktop(text="satır bir\nsatır iki\n", sel=(0, 0), process="Code.exe")
    # VS Code, seçim yokken satırı (sonunda \n ile) kopyalar
    d.send_copy = lambda: d.clipboard.write_text("satır bir\n")
    sel, _ = services(d)
    with pytest.raises(SelectionError):
        sel.capture()


def test_focus_change_during_translation_aborts_without_writing(desktop):
    sel, rep = services(desktop)
    cap = sel.capture()
    desktop.ctx = TargetContext(hwnd=200, focus_hwnd=201, pid=2, process_name="chrome.exe", window_class="Chrome", caret_signature=())
    original = desktop.text
    with pytest.raises(ReplacementError):
        rep.replace(cap, "Hello")
    assert desktop.text == original and "paste" not in desktop.events
    assert desktop.clipboard.data["text"] == "ESKİ PANO"


def test_caret_moved_during_translation_aborts(desktop):
    sel, rep = services(desktop)
    cap = sel.capture()
    desktop.ctx = TargetContext(**{**desktop.ctx.__dict__, "caret_signature": (101, 90, 5, 91, 20)})
    with pytest.raises(ReplacementError):
        rep.replace(cap, "Hello")
    assert "paste" not in desktop.events


def test_focus_changes_right_before_paste_still_restores_clipboard(desktop):
    sel, rep = services(desktop)
    cap = sel.capture()
    calls = {"n": 0}
    real = desktop.foreground

    def flaky():
        calls["n"] += 1
        # 1. doğrulama geçer; yazma sonrası ikinci doğrulamada odak kaybolur
        return real() if calls["n"] <= 1 else TargetContext(hwnd=9, focus_hwnd=9, pid=3, process_name="x", window_class="X", caret_signature=())

    desktop.foreground = flaky
    with pytest.raises(ReplacementError):
        rep.replace(cap, "Hello")
    assert desktop.clipboard.data["text"] == "ESKİ PANO"  # geçici metin panoda kalmadı


def test_clipboard_failure_does_not_lose_text(desktop):
    sel, rep = services(desktop)
    cap = sel.capture()
    desktop.clipboard.fail_write = True
    original = desktop.text
    with pytest.raises(OSError):
        rep.replace(cap, "Hello")
    assert desktop.text == original


def test_empty_translation_never_written(desktop):
    sel, rep = services(desktop)
    cap = sel.capture()
    with pytest.raises(ReplacementError):
        rep.replace(cap, "  ")
    assert desktop.text.startswith("Merhaba dünya")


def test_newline_style_matches_original():
    assert match_newlines("a\r\nb", "x\ny") == "x\r\ny"
    assert match_newlines("a\nb", "x\r\ny") == "x\ny"


def test_multiline_unicode_and_long_text(desktop):
    text = "Günaydın 🙂\r\nİkinci satır — çok uzun " + "ğ" * 20000
    desktop.text = "ÖN " + text + " SON"
    desktop.sel = [3, 3 + len(text)]
    sel, rep = services(desktop)
    cap = sel.capture()
    assert cap.text == text
    rep.replace(cap, "Good morning 🙂\nSecond line")
    assert desktop.text == "ÖN Good morning 🙂\r\nSecond line SON"
