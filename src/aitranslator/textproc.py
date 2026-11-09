"""Metin koruma yardımcıları (satır sonları, girintiler, kod, URL, e-posta).

Çeviri motorları (özellikle Google Translate gibi MT servisleri) satır sonlarını ve kod/URL gibi
öğeleri bozabilir. ``translate_preserving`` metni korunacak/çevrilecek parçalara ayırır, yalnızca
çevrilecek satırları gönderir ve sonucu özgün düzenle yeniden birleştirir.
"""
from __future__ import annotations

import re
from typing import Callable

# Çevrilmemesi gereken parçalar: kod blokları, satır içi kod, URL, e-posta, @kullanıcı, #etiket
PROTECTED_RE = re.compile(
    r"""
    ```.*?```                              # çit kod bloğu
    | `[^`\n]+`                            # satır içi kod
    | \b(?:https?://|www\.)[^\s<>"')]+     # URL
    | [\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+      # e-posta
    | (?<!\w)@[\w.]{2,}                    # kullanıcı adı
    """,
    re.VERBOSE | re.DOTALL,
)

_LINE_RE = re.compile(r"^(\s*)(.*?)(\s*)$", re.DOTALL)


def split_protected(text: str) -> list[tuple[bool, str]]:
    """[(korunmuş_mu, parça), ...] – birleştirildiğinde özgün metni verir."""
    parts: list[tuple[bool, str]] = []
    pos = 0
    for m in PROTECTED_RE.finditer(text):
        if m.start() > pos:
            parts.append((False, text[pos : m.start()]))
        parts.append((True, m.group(0)))
        pos = m.end()
    if pos < len(text):
        parts.append((False, text[pos:]))
    return parts


def _translatable(line: str) -> bool:
    """Harf içermeyen satırlar (yalnızca emoji, sayı, noktalama) çevrilmez."""
    return any(ch.isalpha() for ch in line)


def translate_preserving(text: str, translate_fn: Callable[[str], str]) -> str:
    """``translate_fn`` çok satırlı bir metni çevirir. Burada düzen/koruma işi yapılır.

    Satır sayısı çeviri sonrası tutmazsa satırlar tek tek çevrilir (güvenli geri dönüş).
    """
    pieces = split_protected(text)
    # Çevrilecek tüm satırları topla
    jobs: list[tuple[int, int]] = []  # (parça no, satır no)
    contents: list[str] = []
    layouts: list[list[tuple[str, str, str]] | None] = []
    for pi, (protected, chunk) in enumerate(pieces):
        if protected or not chunk.strip():
            layouts.append(None)
            continue
        lines = chunk.split("\n")
        layout: list[tuple[str, str, str]] = []
        for li, line in enumerate(lines):
            lead, core, trail = _LINE_RE.match(line).groups()  # type: ignore[union-attr]
            layout.append((lead, core, trail))
            if core and _translatable(core):
                jobs.append((pi, li))
                contents.append(core)
        layouts.append(layout)

    if not contents:
        return text

    translated = _translate_lines(contents, translate_fn)

    result: list[str] = []
    cursor = 0
    job_set = {job: i for i, job in enumerate(jobs)}
    for pi, (protected, chunk) in enumerate(pieces):
        layout = layouts[pi]
        if layout is None:
            result.append(chunk)
            continue
        out_lines = []
        for li, (lead, core, trail) in enumerate(layout):
            idx = job_set.get((pi, li))
            if idx is None:
                out_lines.append(lead + core + trail)
            else:
                out_lines.append(lead + translated[idx].strip() + trail)
                cursor += 1
        result.append("\n".join(out_lines))
    return "".join(result)


def _translate_lines(lines: list[str], fn: Callable[[str], str]) -> list[str]:
    joined = "\n".join(lines)
    out = fn(joined)
    split = out.split("\n")
    if len(split) == len(lines):
        return split
    # Satır sayısı bozuldu → tek tek çevir
    return [fn(line) for line in lines]


def chunk_text(text: str, limit: int = 4000) -> list[str]:
    """Metni satır sınırlarında ``limit`` karakteri aşmayacak parçalara böler (tek satır uzunsa cümleden/boşluktan)."""
    chunks: list[str] = []
    current = ""
    for line in text.split("\n"):
        while len(line) > limit:
            cut = max(line.rfind(". ", 0, limit), line.rfind(" ", 0, limit))
            cut = limit if cut <= 0 else cut + 1
            head, line = line[:cut], line[cut:]
            if current:
                chunks.append(current)
                current = ""
            chunks.append(head)
        add = line if not current else "\n" + line
        if len(current) + len(add) > limit and current:
            chunks.append(current)
            current = line
        else:
            current += add
    chunks.append(current)
    return chunks
