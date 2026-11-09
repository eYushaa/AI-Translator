import pytest

from aitranslator.providers import ProviderError, ProviderInterface
from aitranslator.translation_service import TranslationError, TranslationService


class Stub(ProviderInterface):
    def __init__(self, pid, configured=True, result="çeviri", error=None, settings=None, secrets=None):
        super().__init__(lambda: settings, secrets)
        self.id = pid
        self.label = pid.upper()
        self._configured = configured
        self._result = result
        self._error = error
        self.calls = 0

    def is_configured(self):
        return self._configured

    def translate(self, text, target, source="auto"):
        self.calls += 1
        if self._error:
            raise self._error
        return self._result(text) if callable(self._result) else self._result

    def test_connection(self):
        return "ok"


def build(settings, secrets, **provs):
    stubs = {pid: Stub(pid, **kw) for pid, kw in provs.items()}
    stubs.setdefault("google", Stub("google"))
    return TranslationService(settings, secrets, providers=stubs), stubs


def test_nothing_configured_uses_google(settings, secrets):
    settings.settings.providers.active = "gemini"  # seçili ama yapılandırılmamış
    svc, st = build(settings, secrets, gemini={"configured": False})
    r = svc.translate("merhaba", "en")
    assert r.provider_id == "google" and st["gemini"].calls == 0


def test_selected_configured_provider_used(settings, secrets):
    settings.settings.providers.active = "lmstudio"
    svc, st = build(settings, secrets, lmstudio={"result": "LM"})
    assert svc.translate("merhaba", "en").text == "LM"
    assert st["google"].calls == 0


def test_no_silent_fallback_by_default(settings, secrets):
    settings.settings.providers.active = "lmstudio"
    svc, st = build(settings, secrets, lmstudio={"error": ProviderError("unreachable", "LM Studio kapalı")})
    with pytest.raises(TranslationError) as ei:
        svc.translate("gizli metin", "en")
    assert "LM Studio kapalı" in ei.value.message
    assert st["google"].calls == 0  # metin, kullanıcı istemeden başka sağlayıcıya GİTMEDİ


def test_fallback_when_enabled(settings, secrets):
    settings.settings.providers.active = "lmstudio"
    settings.settings.providers.auto_fallback = True
    svc, st = build(settings, secrets, lmstudio={"error": ProviderError("unreachable", "kapalı")})
    r = svc.translate("merhaba", "en")
    assert r.provider_id == "google" and st["lmstudio"].calls == 1


def test_empty_or_runaway_output_rejected(settings, secrets):
    svc, _ = build(settings, secrets, google={"result": "   "})
    with pytest.raises(TranslationError):
        svc.translate("merhaba", "en")
    svc2, _ = build(settings, secrets, google={"result": "x" * 5000})
    with pytest.raises(TranslationError):
        svc2.translate("hi", "en")


def test_cache_hits_and_can_be_disabled(settings, secrets):
    svc, st = build(settings, secrets, google={"result": lambda t: t + "!"})
    svc.translate("a b", "en")
    r = svc.translate("a b", "en")
    assert r.from_cache and st["google"].calls == 1
    svc.translate("a b", "de")  # farklı hedef → önbellek yok
    assert st["google"].calls == 2
    settings.settings.privacy.cache_enabled = False
    svc.translate("a b", "en")
    assert st["google"].calls == 3


def test_blank_text_rejected(settings, secrets):
    svc, _ = build(settings, secrets)
    with pytest.raises(TranslationError):
        svc.translate("   ", "en")


def test_unexpected_exception_does_not_leak(settings, secrets):
    svc, _ = build(settings, secrets, google={"error": RuntimeError("boom")})
    with pytest.raises(TranslationError) as ei:
        svc.translate("merhaba", "en")
    assert "beklenmeyen" in ei.value.message
