"""Google Translate sağlayıcısı – anahtar gerektirmeyen varsayılan yedek.

İki mod:

1. **Anahtarsız (varsayılan):** ``translate.googleapis.com/translate_a/single?client=gtx`` ucu.
   Bu uç **resmî/belgelenmiş bir API DEĞİLDİR**; Google tarafından herhangi bir zamanda değiştirilebilir,
   sınırlandırılabilir veya kapatılabilir ve Google'ın hizmet şartlarına göre ticari/yoğun kullanıma uygun
   olmayabilir. Kişisel ve hafif kullanım için "en iyi çaba" yedeğidir. Metin Google sunucularına gönderilir.
2. **Resmî Cloud Translation API (v2):** Ayarlardan etkinleştirilir, kullanıcının kendi API anahtarı gerekir
   (Google Cloud'da ücretlendirilebilir). Kararlılık/şartlar açısından önerilen yoldur.
"""
from __future__ import annotations

from ..languages import LanguageService
from ..textproc import chunk_text, translate_preserving
from .base import ProviderError, ProviderInterface

FREE_URL = "https://translate.googleapis.com/translate_a/single"
CLOUD_URL = "https://translation.googleapis.com/language/translate/v2"
SECRET_NAME = "google_cloud_api_key"


class GoogleTranslateProvider(ProviderInterface):
    id = "google"
    label = "Google Translate"
    sends_text_offsite = True

    @property
    def use_cloud(self) -> bool:
        return self.settings.providers.google.use_cloud_api

    def is_configured(self) -> bool:
        # Anahtarsız mod her zaman kullanılabilir; resmî mod için anahtar gerekir.
        return self._secrets.has(SECRET_NAME) if self.use_cloud else True

    @staticmethod
    def _code(code: str) -> str:
        code = LanguageService.normalize(code)
        return {"he": "iw"}.get(code, code) if code != "auto" else "auto"

    # ---- ağ çağrıları ---------------------------------------------------------
    def _raise_for_status(self, resp) -> None:
        code = resp.status_code
        if code < 400:
            return
        if code == 429:
            raise ProviderError("quota", "Google Translate: istek sınırı aşıldı (çok fazla istek). Bir süre bekleyin.")
        if code in (401, 403):
            msg = "API anahtarı geçersiz veya yetkisiz." if self.use_cloud else "erişim engellendi (çok sık kullanım olabilir)."
            raise ProviderError("auth" if self.use_cloud else "quota", f"Google Translate: {msg}")
        raise ProviderError("bad_response", f"Google Translate: sunucu hata döndürdü (HTTP {code}).")

    def _free_call(self, text: str, target: str, source: str) -> str:
        resp = self.request(
            "POST",
            FREE_URL,
            params={"client": "gtx", "sl": self._code(source), "tl": self._code(target), "dt": "t"},
            data={"q": text},
        )
        self._raise_for_status(resp)
        try:
            data = resp.json()
            return "".join(seg[0] for seg in data[0] if seg and seg[0])
        except (ValueError, IndexError, TypeError, KeyError) as exc:
            raise ProviderError(
                "bad_response", "Google Translate: beklenmeyen yanıt (servis biçimi değişmiş veya erişim kısıtlanmış olabilir)."
            ) from exc

    def _cloud_call(self, text: str, target: str, source: str) -> str:
        body = {"q": text, "target": self._code(target), "format": "text"}
        if self._code(source) != "auto":
            body["source"] = self._code(source)
        resp = self.request(
            "POST", CLOUD_URL, json=body, headers={"X-goog-api-key": self._secrets.get(SECRET_NAME)}
        )
        self._raise_for_status(resp)
        try:
            return resp.json()["data"]["translations"][0]["translatedText"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError("bad_response", "Google Translate: beklenmeyen yanıt biçimi.") from exc

    # ---- arayüz ---------------------------------------------------------------
    def translate(self, text: str, target: str, source: str = "auto", prompt: str = "") -> str:
        if not self.is_configured():
            raise ProviderError("config", "Google Translate (resmî API): API anahtarı girilmemiş.")
        call = self._cloud_call if self.use_cloud else self._free_call

        def fn(chunk_source: str) -> str:
            return "\n".join(call(c, target, source) for c in chunk_text(chunk_source))

        return translate_preserving(text, fn)

    def test_connection(self) -> str:
        out = self.translate("Merhaba", "en", "auto")
        mode = "resmî Cloud Translation API" if self.use_cloud else "anahtarsız uç nokta"
        return f"Google Translate ({mode}): bağlantı başarılı. Test çıktısı: {out.strip()[:40]}"

    def privacy_note(self) -> str:
        note = super().privacy_note()
        if not self.use_cloud:
            note += " Anahtarsız mod resmî olmayan bir uç noktayı kullanır; süreklilik ve kullanım şartları garanti edilemez."
        return note
