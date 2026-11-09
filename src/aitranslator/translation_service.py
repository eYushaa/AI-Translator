"""TranslationService: sağlayıcı seçimi, isteğe bağlı yedekleme, kısa süreli bellek içi önbellek."""
from __future__ import annotations

import hashlib
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass

from .logging_service import get_logger
from .providers import (
    GeminiProvider,
    GoogleTranslateProvider,
    LMStudioProvider,
    LocalLLMProvider,
    ProviderError,
    ProviderInterface,
)
from .secure_storage import SecureStorage
from .settings import SettingsManager

log = get_logger("translate")

CACHE_TTL_SECONDS = 600
CACHE_MAX_ENTRIES = 64


@dataclass
class TranslationResult:
    text: str
    provider_id: str
    provider_label: str
    from_cache: bool = False
    seconds: float = 0.0


class TranslationError(Exception):
    """Tüm denenen sağlayıcılar başarısız oldu. ``message`` kullanıcıya gösterilebilir."""

    def __init__(self, message: str, kind: str = "failed") -> None:
        super().__init__(message)
        self.message = message
        self.kind = kind


class TranslationService:
    def __init__(self, settings: SettingsManager, secrets: SecureStorage, providers: dict[str, ProviderInterface] | None = None) -> None:
        self._settings = settings
        self._secrets = secrets
        get = lambda: self._settings.settings  # noqa: E731 - ayarlar anında yansısın
        self.providers: dict[str, ProviderInterface] = providers or {
            p.id: p
            for p in (
                GoogleTranslateProvider(get, secrets),
                LocalLLMProvider(get, secrets),
                LMStudioProvider(get, secrets),
                GeminiProvider(get, secrets),
            )
        }
        self._cache: OrderedDict[str, tuple[float, str]] = OrderedDict()
        self._lock = threading.Lock()

    # ---- sağlayıcı seçimi -----------------------------------------------------
    def resolve_chain(self, require_llm: bool = False) -> list[ProviderInterface]:
        ps = self._settings.settings.providers
        active = self.providers.get(ps.active)
        chain: list[ProviderInterface] = []
        if require_llm:
            if active is not None and active.id != "google" and active.is_configured():
                chain.append(active)
            if ps.auto_fallback:
                for pid in ps.fallback_order:
                    if pid != "google":
                        prov = self.providers.get(pid)
                        if prov is not None and prov not in chain and prov.is_configured():
                            chain.append(prov)
            for pid in ("gemini", "lmstudio", "local_llm"):
                prov = self.providers.get(pid)
                if prov is not None and prov not in chain and prov.is_configured():
                    chain.append(prov)
            return chain

        if active is not None and active.is_configured():
            chain = [active]
        else:
            # Seçili sağlayıcı yapılandırılmamış → Google Translate (spesifikasyon: 3. kural)
            chain = [self.providers["google"]]
        if ps.auto_fallback:
            for pid in ps.fallback_order:
                prov = self.providers.get(pid)
                if prov is not None and prov not in chain and prov.is_configured():
                    chain.append(prov)
        return chain

    def active_provider(self) -> ProviderInterface:
        return self.resolve_chain()[0]

    # ---- önbellek -------------------------------------------------------------
    def _cache_key(self, prov: ProviderInterface, text: str, target: str, source: str, prompt_override: str = "") -> str:
        model = ""
        ep = getattr(self._settings.settings.providers, prov.id, None)
        if ep is not None and hasattr(ep, "model"):
            model = ep.model
        prompt = prompt_override if prompt_override else getattr(self._settings.settings.languages, "prompt", "")
        prompt_digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"{prov.id}|{model}|{prompt_digest}|{target}|{source}|{digest}"


    def _cache_get(self, key: str) -> str | None:
        with self._lock:
            hit = self._cache.get(key)
            if not hit:
                return None
            if time.monotonic() - hit[0] > CACHE_TTL_SECONDS:
                del self._cache[key]
                return None
            self._cache.move_to_end(key)
            return hit[1]

    def _cache_put(self, key: str, value: str) -> None:
        with self._lock:
            self._cache[key] = (time.monotonic(), value)
            while len(self._cache) > CACHE_MAX_ENTRIES:
                self._cache.popitem(last=False)

    def clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()

    # ---- çeviri ---------------------------------------------------------------
    @staticmethod
    def _sane(original: str, translated: str) -> bool:
        """Model gevezeliğine/boş çıktıya karşı basit güvenlik: bunlar asla metnin yerine yazılmaz."""
        if not translated.strip():
            return False
        return len(translated) <= 8 * len(original) + 200

    def translate(
        self,
        text: str,
        target: str,
        source: str | None = None,
        prompt_override: str | None = None,
    ) -> TranslationResult:
        if not text or not text.strip():
            raise TranslationError("İşlenecek metin boş.", "empty")
        s = self._settings.settings
        src = "auto" if s.general.auto_detect_source else (source or s.languages.source or "auto")

        if prompt_override:
            chain = self.resolve_chain(require_llm=True)
            if not chain:
                raise TranslationError(
                    "Metin iyileştirme ve imla düzeltme özelliği bir yapay zeka (LLM) modeli gerektirir. "
                    "Lütfen Ayarlar > Sağlayıcılar sayfasından Gemini, LM Studio veya Yerel LLM sağlayıcısını yapılandırın.",
                    "no_llm",
                )
        else:
            chain = self.resolve_chain()

        errors: list[str] = []
        for prov in chain:
            key = self._cache_key(prov, text, target, src, prompt_override or "") if s.privacy.cache_enabled else ""
            if key:
                cached = self._cache_get(key)
                if cached is not None:
                    return TranslationResult(cached, prov.id, prov.label, from_cache=True)
            started = time.monotonic()
            try:
                import inspect
                sig = inspect.signature(prov.translate)
                if "prompt" in sig.parameters:
                    out = prov.translate(text, target, src, prompt=prompt_override or "")
                else:
                    out = prov.translate(text, target, src)
            except ProviderError as exc:
                log.warning("Sağlayıcı hatası provider=%s kind=%s len=%d", prov.id, exc.kind, len(text))
                errors.append(exc.message)
                continue
            except Exception as exc:  # noqa: BLE001 - beklenmeyen hata da orijinali silmemeli
                log.exception("Beklenmeyen sağlayıcı hatası provider=%s", prov.id)
                errors.append(f"{prov.label}: beklenmeyen hata ({type(exc).__name__}).")
                continue
            if not self._sane(text, out):
                errors.append(f"{prov.label}: geçersiz/boş çıktı; metin değiştirilmedi.")
                continue
            if key:
                self._cache_put(key, out)
            return TranslationResult(out, prov.id, prov.label, seconds=time.monotonic() - started)
        raise TranslationError("\n".join(errors) or "İşlem başarısız oldu.")
