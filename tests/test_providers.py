import json

import httpx
import pytest

from aitranslator.providers import (
    GeminiProvider, GoogleTranslateProvider, LMStudioProvider, LocalLLMProvider, ProviderError,
)
from conftest import mock_transport


def make(cls, settings, secrets, handler):
    p = cls(lambda: settings.settings, secrets)
    p.transport = mock_transport(handler)
    return p


# ---------------- LM Studio / OpenAI uyumlu ----------------
def test_lmstudio_translate_and_prompt(settings, secrets):
    settings.settings.providers.lmstudio.model = "qwen"
    seen = {}

    def handler(req: httpx.Request):
        seen["url"] = str(req.url)
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "Hello world"}}]})

    p = make(LMStudioProvider, settings, secrets, handler)
    assert p.translate("Merhaba dünya", "en") == "Hello world"
    assert seen["url"] == "http://localhost:1234/v1/chat/completions"
    assert seen["body"]["model"] == "qwen" and seen["body"]["temperature"] == 0
    assert "English" in seen["body"]["messages"][0]["content"]
    assert seen["body"]["messages"][1]["content"] == "Merhaba dünya"


def test_lmstudio_custom_system_prompt(settings, secrets):
    settings.settings.providers.lmstudio.model = "qwen"
    settings.settings.languages.prompt = "Translate directly to {target}. {source}"
    seen = {}

    def handler(req: httpx.Request):
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "Hello"}}]})

    p = make(LMStudioProvider, settings, secrets, handler)
    assert p.translate("Merhaba", "en", "tr") == "Hello"
    content = seen["body"]["messages"][0]["content"]
    assert content == "Translate directly to English. The source language is Turkish."



def test_llm_output_cleaned_think_tags_and_whitespace(settings, secrets):
    settings.settings.providers.lmstudio.model = "m"
    handler = lambda req: httpx.Response(200, json={"choices": [{"message": {"content": "<think>düşünüyorum</think>\nSelam\n"}}]})  # noqa: E731
    p = make(LMStudioProvider, settings, secrets, handler)
    assert p.translate("  Hello", "tr") == "  Selam"


def test_lmstudio_server_down_message(settings, secrets):
    settings.settings.providers.lmstudio.model = "m"

    def handler(req):
        raise httpx.ConnectError("refused")

    p = make(LMStudioProvider, settings, secrets, handler)
    with pytest.raises(ProviderError) as ei:
        p.translate("x", "en")
    assert ei.value.kind == "unreachable" and "LM Studio" in ei.value.message


def test_lmstudio_model_not_loaded(settings, secrets):
    settings.settings.providers.lmstudio.model = "yok"
    handler = lambda req: httpx.Response(404, json={"error": {"message": "model 'yok' not found"}})  # noqa: E731
    p = make(LMStudioProvider, settings, secrets, handler)
    with pytest.raises(ProviderError) as ei:
        p.translate("x", "en")
    assert ei.value.kind == "model_missing"


def test_lmstudio_list_and_test_connection(settings, secrets):
    settings.settings.providers.lmstudio.model = "a"
    handler = lambda req: httpx.Response(200, json={"data": [{"id": "b"}, {"id": "a"}]})  # noqa: E731
    p = make(LMStudioProvider, settings, secrets, handler)
    assert p.list_models() == ["a", "b"]
    assert "başarılı" in p.test_connection()
    settings.settings.providers.lmstudio.model = "z"
    with pytest.raises(ProviderError) as ei:
        p.test_connection()
    assert ei.value.kind == "model_missing"


def test_local_llm_not_configured_without_model(settings, secrets):
    p = make(LocalLLMProvider, settings, secrets, lambda r: httpx.Response(500))
    assert not p.is_configured()
    with pytest.raises(ProviderError) as ei:
        p.translate("x", "en")
    assert ei.value.kind == "config"


def test_openai_api_key_sent_as_bearer(settings, secrets):
    settings.settings.providers.lmstudio.model = "m"
    secrets.set("lmstudio_api_key", "tok123")
    seen = {}

    def handler(req):
        seen["auth"] = req.headers.get("authorization")
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    make(LMStudioProvider, settings, secrets, handler).translate("x", "en")
    assert seen["auth"] == "Bearer tok123"


def test_timeout_maps_to_error(settings, secrets):
    settings.settings.providers.lmstudio.model = "m"

    def handler(req):
        raise httpx.ReadTimeout("yavaş")

    with pytest.raises(ProviderError) as ei:
        make(LMStudioProvider, settings, secrets, handler).translate("x", "en")
    assert ei.value.kind == "timeout"


# ---------------- Gemini ----------------
def gemini_ok(text):
    return {"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}]}


def test_gemini_translate_key_in_header_not_url(settings, secrets):
    secrets.set("gemini_api_key", "AIzaSECRETKEY")
    seen = {}

    def handler(req: httpx.Request):
        seen["url"] = str(req.url)
        seen["key"] = req.headers.get("x-goog-api-key")
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json=gemini_ok("Hello"))

    p = make(GeminiProvider, settings, secrets, handler)
    assert p.translate("Merhaba", "en") == "Hello"
    assert "AIzaSECRETKEY" not in seen["url"] and seen["key"] == "AIzaSECRETKEY"
    assert ":generateContent" in seen["url"]
    assert "systemInstruction" in seen["body"]


def test_gemini_custom_system_prompt(settings, secrets):
    secrets.set("gemini_api_key", "AIzaSECRETKEY")
    settings.settings.languages.prompt = "Translate quickly to {target}."
    seen = {}

    def handler(req: httpx.Request):
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json=gemini_ok("Hello"))

    p = make(GeminiProvider, settings, secrets, handler)
    assert p.translate("Merhaba", "en") == "Hello"
    parts = seen["body"]["systemInstruction"]["parts"]
    assert parts[0]["text"] == "Translate quickly to English."



@pytest.mark.parametrize(
    "status,body,kind",
    [
        (429, {"error": {"status": "RESOURCE_EXHAUSTED"}}, "quota"),
        (400, {"error": {"message": "API key not valid. Please pass a valid API key."}}, "auth"),
        (403, {"error": {}}, "auth"),
        (404, {"error": {}}, "model_missing"),
    ],
)
def test_gemini_error_mapping(settings, secrets, status, body, kind):
    secrets.set("gemini_api_key", "k")
    p = make(GeminiProvider, settings, secrets, lambda r: httpx.Response(status, json=body))
    with pytest.raises(ProviderError) as ei:
        p.translate("x", "en")
    assert ei.value.kind == kind


def test_gemini_requires_key(settings, secrets):
    p = make(GeminiProvider, settings, secrets, lambda r: httpx.Response(200, json=gemini_ok("x")))
    assert not p.is_configured()
    with pytest.raises(ProviderError) as ei:
        p.translate("x", "en")
    assert ei.value.kind == "config"


def test_gemini_blocked_and_truncated(settings, secrets):
    secrets.set("gemini_api_key", "k")
    blocked = make(GeminiProvider, settings, secrets, lambda r: httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}}))
    with pytest.raises(ProviderError) as ei:
        blocked.translate("x", "en")
    assert ei.value.kind == "blocked"
    cut = {"candidates": [{"content": {"parts": [{"text": "yarım"}]}, "finishReason": "MAX_TOKENS"}]}
    truncated = make(GeminiProvider, settings, secrets, lambda r: httpx.Response(200, json=cut))
    with pytest.raises(ProviderError):
        truncated.translate("x", "en")  # eksik çeviri asla kabul edilmez


def test_gemini_list_models_filters_generate_content(settings, secrets):
    secrets.set("gemini_api_key", "k")
    data = {"models": [
        {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/embedding-001", "supportedGenerationMethods": ["embedContent"]},
    ]}
    p = make(GeminiProvider, settings, secrets, lambda r: httpx.Response(200, json=data))
    assert p.list_models() == ["gemini-2.5-flash"]
    assert "başarılı" in p.test_connection()


# ---------------- Google Translate ----------------
def gt_response(translated_lines):
    # translate_a/single biçimi: [[ [çeviri, orijinal, ...], ... ], null, "tr"]
    return [[[line + ("\n" if i < len(translated_lines) - 1 else ""), "x", None, None] for i, line in enumerate(translated_lines)], None, "tr"]


def test_google_free_preserves_lines_and_protected(settings, secrets):
    calls = []

    def handler(req: httpx.Request):
        q = req.content.decode()
        calls.append(q)
        from urllib.parse import parse_qs

        text = parse_qs(q)["q"][0]
        return httpx.Response(200, json=gt_response([l.upper() for l in text.split("\n")]))

    p = make(GoogleTranslateProvider, settings, secrets, handler)
    out = p.translate("merhaba\n\nnasılsın https://ornek.com ?", "en")
    assert out.split("\n")[0] == "MERHABA" and out.split("\n")[1] == ""
    assert "https://ornek.com" in out  # URL çevriye girmedi


def test_google_free_line_mismatch_fallback(settings, secrets):
    from urllib.parse import parse_qs

    def handler(req):
        text = parse_qs(req.content.decode())["q"][0]
        if "\n" in text:  # çok satırlı istekte servis satırları birleştirir
            return httpx.Response(200, json=[[[text.replace("\n", " ").upper(), "x"]], None, "tr"])
        return httpx.Response(200, json=[[[text.upper(), "x"]], None, "tr"])

    p = make(GoogleTranslateProvider, settings, secrets, handler)
    assert p.translate("bir\niki", "en") == "BIR\nIKI"


def test_google_quota_and_bad_html_response(settings, secrets):
    p = make(GoogleTranslateProvider, settings, secrets, lambda r: httpx.Response(429))
    with pytest.raises(ProviderError) as ei:
        p.translate("merhaba", "en")
    assert ei.value.kind == "quota"
    p2 = make(GoogleTranslateProvider, settings, secrets, lambda r: httpx.Response(200, text="<html>captcha</html>"))
    with pytest.raises(ProviderError) as ei2:
        p2.translate("merhaba", "en")
    assert ei2.value.kind == "bad_response"


def test_google_default_works_without_any_config(settings, secrets):
    p = make(GoogleTranslateProvider, settings, secrets, lambda r: httpx.Response(200, json=[[["Hello", "Merhaba"]], None, "tr"]))
    assert p.is_configured()
    assert p.translate("Merhaba", "en") == "Hello"


def test_google_cloud_mode_needs_key_and_uses_header(settings, secrets):
    settings.settings.providers.google.use_cloud_api = True
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        seen["key"] = req.headers.get("x-goog-api-key")
        return httpx.Response(200, json={"data": {"translations": [{"translatedText": "Hello"}]}})

    p = make(GoogleTranslateProvider, settings, secrets, handler)
    assert not p.is_configured()
    secrets.set("google_cloud_api_key", "CLOUDKEY")
    assert p.translate("Merhaba", "en") == "Hello"
    assert "CLOUDKEY" not in seen["url"] and seen["key"] == "CLOUDKEY"
