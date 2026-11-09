from aitranslator.textproc import chunk_text, split_protected, translate_preserving


def fake_mt(chunk: str) -> str:
    """Her kelimeyi büyük harfe çeviren sahte MT; satır sayısını korur."""
    return chunk.upper()


def test_split_protected_roundtrip():
    text = "Bak https://example.com/a?b=1 ve `kod` ile ali@site.com @kullanici"
    parts = split_protected(text)
    assert "".join(p for _, p in parts) == text
    protected = [p for flag, p in parts if flag]
    assert "https://example.com/a?b=1" in protected and "`kod`" in protected and "ali@site.com" in protected


def test_newlines_indent_and_emoji_preserved():
    text = "  merhaba dünya\r\n\r\n🙂🙂\r\n    ikinci satır  \n"
    out = translate_preserving(text, fake_mt)
    assert out == "  MERHABA DÜNYA\r\n\r\n🙂🙂\r\n    IKINCI SATIR  \n"
    assert out.count("\n") == text.count("\n")


def test_code_blocks_and_urls_untouched():
    text = "metin\n```python\nprint('merhaba')\n```\nson https://x.io/yol"
    out = translate_preserving(text, fake_mt)
    assert "print('merhaba')" in out and "https://x.io/yol" in out
    assert out.startswith("METIN")


def test_line_count_mismatch_falls_back_to_per_line():
    calls = []

    def flaky(chunk: str) -> str:
        calls.append(chunk)
        return chunk.upper().replace("\n", " ") if "\n" in chunk else chunk.upper()

    out = translate_preserving("bir\niki\nüç", flaky)
    assert out.split("\n") == ["BIR", "IKI", "ÜÇ"]
    assert len(out.split("\n")) == 3


def test_no_translatable_text_returned_as_is():
    assert translate_preserving("123 😀 ...", fake_mt) == "123 😀 ..."


def test_chunk_text_respects_limit_and_loses_nothing():
    text = "\n".join("satır %d " % i + "x" * 50 for i in range(200))
    chunks = chunk_text(text, 500)
    assert all(len(c) <= 500 for c in chunks)
    assert "\n".join(chunks) == text


def test_chunk_text_long_single_line():
    text = ("kelime " * 2000).strip()
    chunks = chunk_text(text, 1000)
    assert all(len(c) <= 1000 for c in chunks)
    assert "".join(chunks).replace(" ", "") == text.replace(" ", "")
