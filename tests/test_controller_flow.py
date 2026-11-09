from aitranslator.controller import TranslationController
from aitranslator.history import HistoryStore
from aitranslator.providers import ProviderError
from aitranslator.replacement import TextReplacementService
from aitranslator.selection import TextSelectionService
from aitranslator.translation_service import TranslationService
from test_translation_service import Stub


def build(settings, secrets, desktop, tmp_path, **kw):
    google = Stub("google", **kw)
    svc = TranslationService(settings, secrets, providers={"google": google})
    sel = TextSelectionService(desktop.clipboard, desktop, desktop, sleep=lambda s: None, copy_timeout=0.2)
    rep = TextReplacementService(desktop.clipboard, desktop, desktop, sleep=lambda s: None)
    notes = []
    ctl = TranslationController(settings, svc, sel, rep, HistoryStore(tmp_path / "h.jsonl"), lambda t, m, l: notes.append((t, m, l)))
    return ctl, notes, google


def test_alt_b_end_to_end_notepad_scenario(settings, secrets, desktop, tmp_path):
    desktop.text = "Merhaba dünya. Bu bir testtir."
    ctl, notes, _ = build(settings, secrets, desktop, tmp_path, result="Hello world")
    assert ctl.run_job("alt_b")
    assert desktop.text == "Hello world. Bu bir testtir."
    assert notes[-1][0] == "Çeviri tamamlandı"
    assert ctl.last_translation == "Hello world"


def test_alt_n_uses_its_own_target_language(settings, secrets, desktop, tmp_path):
    settings.settings.languages.alt_n_target = "de"
    targets = []
    ctl, _, google = build(settings, secrets, desktop, tmp_path, result="x")
    google.translate = lambda text, target, source="auto": (targets.append(target), "Hallo")[1]
    ctl.run_job("alt_b")
    ctl.run_job("alt_n")
    assert targets == ["en", "de"]


def test_provider_failure_keeps_original_text(settings, secrets, desktop, tmp_path):
    ctl, notes, _ = build(settings, secrets, desktop, tmp_path, error=ProviderError("unreachable", "Sunucuya ulaşılamadı"))
    original = desktop.text
    assert not ctl.run_job("alt_b")
    assert desktop.text == original and "paste" not in desktop.events
    assert desktop.clipboard.data["text"] == "ESKİ PANO"
    assert notes[-1][2] == "error" and "orijinal metin korundu" in notes[-1][0]


def test_no_selection_notifies_and_changes_nothing(settings, secrets, desktop, tmp_path):
    desktop.sel = [0, 0]
    ctl, notes, google = build(settings, secrets, desktop, tmp_path)
    assert not ctl.run_job("alt_b")
    assert google.calls == 0 and notes[-1][2] == "error"


def test_history_off_by_default_and_on_when_enabled(settings, secrets, desktop, tmp_path):
    ctl, _, _ = build(settings, secrets, desktop, tmp_path, result="Hello")
    ctl.run_job("alt_b")
    assert not (tmp_path / "h.jsonl").exists()
    settings.settings.privacy.history_enabled = True
    desktop.sel = [0, 5]
    ctl.run_job("alt_b")
    store = HistoryStore(tmp_path / "h.jsonl")
    assert len(store.entries()) == 1
    store.clear()
    assert store.entries() == []


def test_concurrent_job_rejected(settings, secrets, desktop, tmp_path):
    ctl, notes, _ = build(settings, secrets, desktop, tmp_path)
    ctl._busy.acquire()
    assert not ctl.run_job("alt_b")
    assert "sürüyor" in notes[-1][1]


def test_alt_n_shows_popup_without_modifying_text(settings, secrets, desktop, tmp_path):
    popups = []
    google = Stub("google", result="Hello popup")
    svc = TranslationService(settings, secrets, providers={"google": google})
    sel = TextSelectionService(desktop.clipboard, desktop, desktop, sleep=lambda s: None, copy_timeout=0.2)
    rep = TextReplacementService(desktop.clipboard, desktop, desktop, sleep=lambda s: None)
    notes = []
    ctl = TranslationController(
        settings, svc, sel, rep, HistoryStore(tmp_path / "h.jsonl"),
        lambda t, m, l: notes.append((t, m, l)),
        show_popup=lambda orig, trans, tgt, prov: popups.append((orig, trans, tgt, prov)),
    )
    desktop.text = "Baskasinin yazdigi yazi"
    desktop.sel = [0, len(desktop.text)]
    assert ctl.run_job("alt_n")
    # Orijinal metin değiştirilmemeli (salt-okunur / başkasının metni)
    assert desktop.text == "Baskasinin yazdigi yazi"
    assert "paste" not in desktop.events
    assert len(popups) == 1
    assert popups[0][0] == "Baskasinin yazdigi yazi"
    assert popups[0][1] == "Hello popup"
    assert popups[0][2] == "en"

