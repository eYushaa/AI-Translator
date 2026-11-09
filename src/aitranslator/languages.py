"""LanguageService: desteklenen diller, arama ve hafif dil tahmini."""
from __future__ import annotations

import unicodedata

from .i18n import get_ui_language, t

# (kod, Türkçe ad, ana dilde ad)
LANGUAGES: list[tuple[str, str, str]] = [
    ("af", "Afrikaanca", "Afrikaans"), ("sq", "Arnavutça", "Shqip"), ("ar", "Arapça", "العربية"),
    ("az", "Azerbaycanca", "Azərbaycan"), ("eu", "Baskça", "Euskara"), ("be", "Belarusça", "Беларуская"),
    ("bn", "Bengalce", "বাংলা"), ("bs", "Boşnakça", "Bosanski"), ("bg", "Bulgarca", "Български"),
    ("ca", "Katalanca", "Català"), ("zh-CN", "Çince (Basitleştirilmiş)", "简体中文"),
    ("zh-TW", "Çince (Geleneksel)", "繁體中文"), ("hr", "Hırvatça", "Hrvatski"), ("cs", "Çekçe", "Čeština"),
    ("da", "Danca", "Dansk"), ("nl", "Felemenkçe", "Nederlands"), ("en", "İngilizce", "English"),
    ("et", "Estonca", "Eesti"), ("fi", "Fince", "Suomi"), ("fr", "Fransızca", "Français"),
    ("gl", "Galiçyaca", "Galego"), ("ka", "Gürcüce", "ქართული"), ("de", "Almanca", "Deutsch"),
    ("el", "Yunanca", "Ελληνικά"), ("gu", "Güceratça", "ગુજરાતી"), ("he", "İbranice", "עברית"),
    ("hi", "Hintçe", "हिन्दी"), ("hu", "Macarca", "Magyar"), ("is", "İzlandaca", "Íslenska"),
    ("id", "Endonezce", "Bahasa Indonesia"), ("ga", "İrlandaca", "Gaeilge"), ("it", "İtalyanca", "Italiano"),
    ("ja", "Japonca", "日本語"), ("kk", "Kazakça", "Қазақша"), ("ko", "Korece", "한국어"),
    ("ky", "Kırgızca", "Кыргызча"), ("lv", "Letonca", "Latviešu"), ("lt", "Litvanca", "Lietuvių"),
    ("mk", "Makedonca", "Македонски"), ("ms", "Malayca", "Bahasa Melayu"), ("mt", "Maltaca", "Malti"),
    ("mn", "Moğolca", "Монгол"), ("ne", "Nepalce", "नेपाली"), ("no", "Norveççe", "Norsk"),
    ("fa", "Farsça", "فارسی"), ("pl", "Lehçe", "Polski"), ("pt", "Portekizce", "Português"),
    ("pa", "Pencapça", "ਪੰਜਾਬੀ"), ("ro", "Romence", "Română"), ("ru", "Rusça", "Русский"),
    ("sr", "Sırpça", "Српски"), ("sk", "Slovakça", "Slovenčina"), ("sl", "Slovence", "Slovenščina"),
    ("es", "İspanyolca", "Español"), ("sw", "Svahili", "Kiswahili"), ("sv", "İsveççe", "Svenska"),
    ("tl", "Filipince", "Filipino"), ("ta", "Tamilce", "தமிழ்"), ("te", "Teluguca", "తెలుగు"),
    ("th", "Tayca", "ไทย"), ("tr", "Türkçe", "Türkçe"), ("uk", "Ukraynaca", "Українська"),
    ("ur", "Urduca", "اردو"), ("uz", "Özbekçe", "Oʻzbek"), ("vi", "Vietnamca", "Tiếng Việt"),
    ("cy", "Galce", "Cymraeg"),
]

# Dil adlarında İngilizce karşılık (LLM istemlerinde kullanılır)
ENGLISH_NAMES = {
    "af": "Afrikaans", "sq": "Albanian", "ar": "Arabic", "az": "Azerbaijani", "eu": "Basque", "be": "Belarusian",
    "bn": "Bengali", "bs": "Bosnian", "bg": "Bulgarian", "ca": "Catalan", "zh-CN": "Simplified Chinese",
    "zh-TW": "Traditional Chinese", "hr": "Croatian", "cs": "Czech", "da": "Danish", "nl": "Dutch",
    "en": "English", "et": "Estonian", "fi": "Finnish", "fr": "French", "gl": "Galician", "ka": "Georgian",
    "de": "German", "el": "Greek", "gu": "Gujarati", "he": "Hebrew", "hi": "Hindi", "hu": "Hungarian",
    "is": "Icelandic", "id": "Indonesian", "ga": "Irish", "it": "Italian", "ja": "Japanese", "kk": "Kazakh",
    "ko": "Korean", "ky": "Kyrgyz", "lv": "Latvian", "lt": "Lithuanian", "mk": "Macedonian", "ms": "Malay",
    "mt": "Maltese", "mn": "Mongolian", "ne": "Nepali", "no": "Norwegian", "fa": "Persian", "pl": "Polish",
    "pt": "Portuguese", "pa": "Punjabi", "ro": "Romanian", "ru": "Russian", "sr": "Serbian", "sk": "Slovak",
    "sl": "Slovenian", "es": "Spanish", "sw": "Swahili", "sv": "Swedish", "tl": "Filipino", "ta": "Tamil",
    "te": "Telugu", "th": "Thai", "tr": "Turkish", "uk": "Ukrainian", "ur": "Urdu", "uz": "Uzbek",
    "vi": "Vietnamese", "cy": "Welsh",
}

_BY_CODE = {code.lower(): code for code, _, _ in LANGUAGES}
_ALIASES = {"zh": "zh-CN", "iw": "he", "jw": "jv", "nb": "no", "fil": "tl"}


def _fold(text: str) -> str:
    """Büyük/küçük harf ve aksan duyarsız karşılaştırma (İ/ı dahil)."""
    text = text.replace("İ", "i").replace("I", "ı").lower().replace("ı", "i")
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


class LanguageService:
    languages = LANGUAGES

    @staticmethod
    def normalize(code: str) -> str:
        """Kullanıcı/servis dil kodunu desteklenen biçime çevirir; bilinmiyorsa olduğu gibi döner."""
        code = (code or "").strip()
        if not code or code.lower() == "auto":
            return "auto"
        low = code.replace("_", "-").lower()
        if low in _BY_CODE:
            return _BY_CODE[low]
        if low in _ALIASES:
            return _ALIASES[low]
        base = low.split("-")[0]
        return _BY_CODE.get(base, _ALIASES.get(base, code))

    @staticmethod
    def display_name(code: str) -> str:
        code = LanguageService.normalize(code)
        ui_lang = get_ui_language()
        for c, tr, native in LANGUAGES:
            if c == code:
                if ui_lang == "tr":
                    return f"{tr} ({native})" if tr != native else tr
                en = ENGLISH_NAMES.get(c, tr)
                return f"{native} ({en})" if native != en else native
        return t("auto_detect") if code == "auto" else code

    @staticmethod
    def english_name(code: str) -> str:
        code = LanguageService.normalize(code)
        return ENGLISH_NAMES.get(code, code)

    @staticmethod
    def search(query: str) -> list[tuple[str, str, str]]:
        q = _fold(query.strip())
        if not q:
            return list(LANGUAGES)
        return [
            item
            for item in LANGUAGES
            if q in _fold(item[0]) or q in _fold(item[1]) or q in _fold(item[2]) or q in _fold(ENGLISH_NAMES.get(item[0], ""))
        ]

    @staticmethod
    def guess_language(text: str) -> str:
        """Çok hafif, betik tabanlı tahmin. Yalnızca bildirim/geçmiş amaçlıdır; çeviri kararı vermez."""
        counts: dict[str, int] = {}
        for ch in text:
            if not ch.isalpha():
                continue
            cp = ord(ch)
            if 0x0400 <= cp <= 0x04FF:
                key = "ru"
            elif 0x0600 <= cp <= 0x06FF:
                key = "ar"
            elif 0x0590 <= cp <= 0x05FF:
                key = "he"
            elif 0x3040 <= cp <= 0x30FF:
                key = "ja"
            elif 0xAC00 <= cp <= 0xD7AF:
                key = "ko"
            elif 0x4E00 <= cp <= 0x9FFF:
                key = "zh-CN"
            elif 0x0E00 <= cp <= 0x0E7F:
                key = "th"
            elif ch in "ğĞşŞıİ":
                key = "tr"
            else:
                key = "latin"
            counts[key] = counts.get(key, 0) + 1
        if not counts:
            return "auto"
        if counts.get("tr"):
            return "tr"
        best = max(counts, key=counts.get)  # type: ignore[arg-type]
        return "auto" if best == "latin" else best
