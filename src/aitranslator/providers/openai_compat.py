"""OpenAI uyumlu (chat/completions) sunucular için ortak sağlayıcı: Yerel LLM ve LM Studio."""
from __future__ import annotations

from .base import ProviderError, ProviderInterface
from .prompts import clean_llm_output, system_prompt


class OpenAICompatProvider(ProviderInterface):
    sends_text_offsite = False
    #: settings.providers altındaki alan adı ve gizli depo anahtarı
    settings_key = ""
    secret_name = ""
    name_for_errors = ""

    # --- yapılandırma -------------------------------------------------------
    @property
    def endpoint(self):
        return getattr(self.settings.providers, self.settings_key)

    @property
    def base_url(self) -> str:
        return self.endpoint.base_url.strip().rstrip("/")

    @property
    def model(self) -> str:
        return self.endpoint.model.strip()

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        key = self._secrets.get(self.secret_name)
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return headers

    def is_configured(self) -> bool:
        return bool(self.base_url and self.model)

    def _unreachable_message(self) -> str:
        return (
            f"{self.label}: {self.base_url or 'adres girilmemiş'} adresine ulaşılamadı. "
            "Sunucunun çalıştığından ve adresin doğru olduğundan emin olun."
        )

    # --- hata eşleme -----------------------------------------------------------
    def _raise_for_status(self, resp) -> None:
        if resp.status_code < 400:
            return
        body = resp.text[:500].lower()
        code = resp.status_code
        if code in (401, 403):
            raise ProviderError("auth", f"{self.label}: kimlik doğrulama başarısız. API anahtarını kontrol edin.")
        if code == 429:
            raise ProviderError("quota", f"{self.label}: istek sınırı aşıldı, biraz sonra tekrar deneyin.")
        if code in (400, 404) and ("model" in body):
            raise ProviderError(
                "model_missing",
                f"{self.label}: '{self.model}' modeli bulunamadı veya yüklü değil. Modeli yükleyin ya da ayarlardan başka bir model seçin.",
            )
        if code == 404:
            raise ProviderError("config", f"{self.label}: uç nokta bulunamadı (404). API adresi '/v1' ile bitmeli.")
        raise ProviderError("bad_response", f"{self.label}: sunucu hata döndürdü (HTTP {code}).")

    # --- işlemler ---------------------------------------------------------------
    def translate(self, text: str, target: str, source: str = "auto", prompt: str = "") -> str:
        if not self.is_configured():
            raise ProviderError("config", f"{self.label}: API adresi ve model adı ayarlanmamış.")
        prompt_tmpl = prompt.strip() if prompt and prompt.strip() else getattr(self.settings.languages, "prompt", "")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt(target, source, prompt_tmpl)},
                {"role": "user", "content": text},
            ],
            "temperature": 0,
            "stream": False,
        }
        resp = self.request("POST", f"{self.base_url}/chat/completions", json=payload, headers=self._headers())
        self._raise_for_status(resp)
        try:
            content = resp.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError("bad_response", f"{self.label}: beklenmeyen yanıt biçimi.") from exc
        if not isinstance(content, str) or not content.strip():
            raise ProviderError("bad_response", f"{self.label}: model boş yanıt döndürdü.")
        return clean_llm_output(content, text)

    def list_models(self) -> list[str]:
        if not self.base_url:
            raise ProviderError("config", f"{self.label}: API adresi girilmemiş.")
        resp = self.request("GET", f"{self.base_url}/models", headers=self._headers())
        self._raise_for_status(resp)
        try:
            return sorted(str(m["id"]) for m in resp.json()["data"])
        except (ValueError, KeyError, TypeError) as exc:
            raise ProviderError("bad_response", f"{self.label}: model listesi okunamadı.") from exc

    def test_connection(self) -> str:
        models = self.list_models()
        if not models:
            return f"{self.label}: bağlantı başarılı ancak yüklü model görünmüyor."
        if self.model and self.model not in models:
            raise ProviderError(
                "model_missing",
                f"{self.label}: bağlantı başarılı fakat '{self.model}' modeli listede yok. Mevcut modeller: {', '.join(models[:5])}",
            )
        return f"{self.label}: bağlantı başarılı ({len(models)} model bulundu)."


class LocalLLMProvider(OpenAICompatProvider):
    id = "local_llm"
    label = "Yerel LLM"
    settings_key = "local_llm"
    secret_name = "local_llm_api_key"


class LMStudioProvider(OpenAICompatProvider):
    id = "lmstudio"
    label = "LM Studio"
    settings_key = "lmstudio"
    secret_name = "lmstudio_api_key"

    def _unreachable_message(self) -> str:
        return (
            f"LM Studio'ya ulaşılamadı ({self.base_url}). LM Studio'yu açın, Developer sekmesinden "
            "yerel sunucuyu (Start Server) başlatın ve modeli yükleyin."
        )
