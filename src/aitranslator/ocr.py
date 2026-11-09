"""OCR (Optik Karakter Tanıma) Servisi: Ekrandan kırpılan görüntülerden metin okur.

Öncelik sırası:
1. Windows Yerel OCR (Windows.Media.Ocr / winocr) - son derece hızlı, çevrimdışı, yerel.
2. Gemini Vision OCR (Google Gemini yapılandırılmışsa) - yapay zeka tabanlı, 100+ dilde olağanüstü doğruluk.
"""
from __future__ import annotations

import asyncio
import base64
from typing import Any

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QImage

from .logging_service import get_logger

log = get_logger("ocr")


def qimage_to_png_bytes(image: QImage) -> bytes:
    """QImage nesnesini PNG formatında baytlara dönüştürür."""
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buf, "PNG")
    return bytes(ba.data())


class OcrService:
    def __init__(self, gemini_provider: Any = None) -> None:
        self._gemini = gemini_provider

    @staticmethod
    def get_installed_windows_ocr_languages() -> list[str]:
        """Sistemde kurulu Windows OCR dillerini döndürür (örn. ['tr-TR', 'en-US'])."""
        try:
            import winocr
            return [lang.language_tag for lang in winocr.OcrEngine.available_recognizer_languages]
        except Exception:
            return []

    def extract_text(
        self,
        image: QImage,
        lang_hint: str = "",
        engine: str = "auto",
        fallback_to_ai: bool = True,
    ) -> str:
        """Görüntüdeki metni tanır.
        engine: 'auto', 'windows', 'gemini'
        fallback_to_ai: Yerel OCR başarısız olursa Gemini Vision'a geç
        """
        if image.isNull() or image.width() < 4 or image.height() < 4:
            return ""

        # 1. Yalnızca Gemini Vision seçildiyse
        if engine == "gemini":
            if self._gemini is not None and getattr(self._gemini, "is_configured", lambda: False)():
                try:
                    gemini_text = self._extract_with_gemini(image)
                    if gemini_text.strip():
                        log.info("Gemini Vision OCR başarılı len=%d", len(gemini_text))
                        return gemini_text.strip()
                except Exception:
                    log.exception("Gemini Vision OCR başarısız")
            return ""

        # 2. Yerel Windows OCR (winocr) - 'auto' veya 'windows' modu
        text = self._extract_with_winocr(image, lang_hint)
        if text.strip():
            log.info("Windows OCR başarılı len=%d", len(text))
            return text.strip()

        # 3. Gemini Vision OCR Fallback
        if fallback_to_ai and engine in ("auto", "windows"):
            if self._gemini is not None and getattr(self._gemini, "is_configured", lambda: False)():
                try:
                    gemini_text = self._extract_with_gemini(image)
                    if gemini_text.strip():
                        log.info("Gemini Vision OCR (yedek) başarılı len=%d", len(gemini_text))
                        return gemini_text.strip()
                except Exception:
                    log.exception("Gemini Vision OCR başarısız")

        return text.strip()

    def _extract_with_winocr(self, image: QImage, lang_hint: str = "") -> str:
        try:
            import winocr
        except ImportError:
            log.warning("winocr paketi yüklü değil")
            return ""

        try:
            w, h = image.width(), image.height()
            img_rgba = image.convertToFormat(QImage.Format.Format_RGBA8888)
            raw_data = bytes(img_rgba.constBits())

            async def _run_ocr() -> str:
                # Kullanılabilir motorları topla
                engines = []
                user_engine = winocr.OcrEngine.try_create_from_user_profile_languages()
                if user_engine:
                    engines.append(user_engine)

                for lang in winocr.OcrEngine.available_recognizer_languages:
                    if lang_hint and lang_hint.lower() in lang.language_tag.lower():
                        eng = winocr.OcrEngine.try_create_from_language(lang)
                        if eng and eng not in engines:
                            engines.insert(0, eng)
                    else:
                        eng = winocr.OcrEngine.try_create_from_language(lang)
                        if eng and eng not in engines:
                            engines.append(eng)

                if not engines:
                    return ""

                # Sırayla dene, ilk anlamlı metin üreteni al
                best_text = ""
                for eng in engines:
                    writer = winocr.DataWriter()
                    writer.write_bytes(raw_data)
                    sb = winocr.SoftwareBitmap.create_copy_from_buffer(
                        writer.detach_buffer(), winocr.BitmapPixelFormat.RGBA8, w, h
                    )
                    res = await eng.recognize_async(sb)
                    txt = (res.text or "").strip()
                    if len(txt) > len(best_text):
                        best_text = txt
                    if best_text:
                        break
                return best_text

            return asyncio.run(_run_ocr())
        except Exception:
            log.exception("Windows OCR çalışma hatası")
            return ""

    def _extract_with_gemini(self, image: QImage) -> str:
        png_bytes = qimage_to_png_bytes(image)
        b64_str = base64.b64encode(png_bytes).decode("ascii")

        prompt = (
            "Extract all text visible in this image accurately and verbatim. "
            "Do not add any descriptions, headers, intros, notes or markdown wrapper. "
            "Output ONLY the plain extracted text."
        )

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"inlineData": {"mimeType": "image/png", "data": b64_str}},
                        {"text": prompt},
                    ],
                }
            ],
            "generationConfig": {"temperature": 0},
        }

        resp = self._gemini.request(
            "POST",
            f"{self._gemini.base_url}/models/{self._gemini.model}:generateContent",
            json=payload,
            headers=self._gemini._headers(),
        )
        self._gemini._raise_for_status(resp)
        data = resp.json()
        cand = data["candidates"][0]
        parts = cand["content"]["parts"]
        return "".join(p.get("text", "") for p in parts if not p.get("thought"))

