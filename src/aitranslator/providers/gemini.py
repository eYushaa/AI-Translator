"""Google Gemini API sağlayıcısı (kullanıcının kendi API anahtarıyla)."""
from __future__ import annotations

from .base import ProviderError, ProviderInterface
from .prompts import clean_llm_output, system_prompt

SECRET_NAME = "gemini_api_key"


class GeminiProvider(ProviderInterface):
    id = "gemini"
    label = "Google Gemini"
    sends_text_offsite = True

    @property
    def base_url(self) -> str:
        return self.settings.providers.gemini.base_url.strip().rstrip("/")

    @property
    def model(self) -> str:
        m = self.settings.providers.gemini.model.strip()
        return m[len("models/") :] if m.startswith("models/") else m

    def _headers(self) -> dict[str, str]:
        # Anahtar URL'de değil başlıkta gönderilir; böylece günlüklere/proxy kayıtlarına sızmaz.
        return {"x-goog-api-key": self._secrets.get(SECRET_NAME), "Content-Type": "application/json"}

    def is_configured(self) -> bool:
        return bool(self._secrets.has(SECRET_NAME) and self.model and self.base_url)

    def _raise_for_status(self, resp) -> None:
        if resp.status_code < 400:
            return
        code = resp.status_code
        body = resp.text[:800]
        if code == 429 or "RESOURCE_EXHAUSTED" in body:
            raise ProviderError("quota", "Gemini: API kotası aşıldı. Bir süre bekleyin ya da kotanızı/planınızı kontrol edin.")
        if code in (401, 403) or "API_KEY_INVALID" in body or "API key not valid" in body:
            raise ProviderError("auth", "Gemini: API anahtarı geçersiz veya yetkisiz. Anahtarı ayarlardan kontrol edin.")
        if code == 404:
            raise ProviderError("model_missing", f"Gemini: '{self.model}' modeli bulunamadı. Model adını ayarlardan güncelleyin.")
        if code == 400:
            raise ProviderError("bad_response", "Gemini: istek reddedildi (HTTP 400). Model adını ve metni kontrol edin.")
        raise ProviderError("bad_response", f"Gemini: sunucu hata döndürdü (HTTP {code}).")

    def translate(self, text: str, target: str, source: str = "auto", prompt: str = "") -> str:
        if not self.is_configured():
            raise ProviderError("config", "Gemini: API anahtarı veya model ayarlanmamış.")
        prompt_tmpl = prompt.strip() if prompt and prompt.strip() else getattr(self.settings.languages, "prompt", "")
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt(target, source, prompt_tmpl)}]},
            "contents": [{"role": "user", "parts": [{"text": text}]}],
            "generationConfig": {"temperature": 0},
        }
        resp = self.request(
            "POST", f"{self.base_url}/models/{self.model}:generateContent", json=payload, headers=self._headers()
        )
        self._raise_for_status(resp)
        try:
            data = resp.json()
        except ValueError as exc:
            raise ProviderError("bad_response", "Gemini: yanıt okunamadı.") from exc
        block = (data.get("promptFeedback") or {}).get("blockReason")
        if block:
            raise ProviderError("blocked", f"Gemini: içerik güvenlik filtresi nedeniyle engellendi ({block}).")
        try:
            cand = data["candidates"][0]
            parts = cand["content"]["parts"]
            content = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        except (KeyError, IndexError, TypeError) as exc:
            reason = ""
            try:
                reason = data["candidates"][0].get("finishReason", "")
            except (KeyError, IndexError, TypeError, AttributeError):
                pass
            if reason in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST"):
                raise ProviderError("blocked", "Gemini: içerik güvenlik filtresi nedeniyle engellendi.") from exc
            raise ProviderError("bad_response", "Gemini: beklenmeyen yanıt biçimi.") from exc
        if cand.get("finishReason") == "MAX_TOKENS":
            raise ProviderError("bad_response", "Gemini: yanıt uzunluk sınırında kesildi; çeviri eksik olabilir, işlem iptal edildi.")
        if not content.strip():
            raise ProviderError("bad_response", "Gemini: boş yanıt döndü.")
        return clean_llm_output(content, text)

    def list_models(self) -> list[str]:
        if not self._secrets.has(SECRET_NAME):
            raise ProviderError("config", "Gemini: API anahtarı girilmemiş.")
        resp = self.request("GET", f"{self.base_url}/models", headers=self._headers(), params={"pageSize": 100})
        self._raise_for_status(resp)
        try:
            return sorted(
                m["name"].removeprefix("models/")
                for m in resp.json().get("models", [])
                if "generateContent" in m.get("supportedGenerationMethods", [])
            )
        except (ValueError, KeyError, TypeError) as exc:
            raise ProviderError("bad_response", "Gemini: model listesi okunamadı.") from exc

    def test_connection(self) -> str:
        models = self.list_models()
        if self.model and models and self.model not in models:
            raise ProviderError(
                "model_missing",
                f"Gemini: anahtar geçerli ama '{self.model}' modeli kullanılabilir değil. Örnekler: {', '.join(models[:5])}",
            )
        return f"Gemini: bağlantı başarılı ({len(models)} model kullanılabilir)."
