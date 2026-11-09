"""LoggingService: hassas veri (API anahtarı, token, kullanıcı metni) yazmayan günlükleme.

Kural: Çevrilen metnin içeriği asla günlüğe yazılmaz; yalnızca uzunluk gibi metaveri yazılır.
Buna ek olarak, yanlışlıkla bir anahtar mesaja sızarsa RedactingFilter onu maskeler.
"""
from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler

from .paths import log_path

_PATTERNS = [
    (re.compile(r"AIza[0-9A-Za-z_\-]{20,}"), "AIza***"),
    (re.compile(r"sk-[A-Za-z0-9_\-]{12,}"), "sk-***"),
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]{8,}"), r"\1***"),
    (re.compile(r"(?i)(x-goog-api-key['\"]?\s*[:=]\s*['\"]?)[^\s'\",}]+"), r"\1***"),
    (re.compile(r"(?i)([?&]key=)[^&\s]+"), r"\1***"),
    (re.compile(r"(?i)(api[_-]?key['\"]?\s*[:=]\s*['\"]?)[^\s'\",}]+"), r"\1***"),
    (re.compile(r"(?i)(password|token|secret)(['\"]?\s*[:=]\s*['\"]?)[^\s'\",}]+"), r"\1\2***"),
]


def redact(text: str) -> str:
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    return text


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # biçimlendirme hatası günlüğü düşürmemeli
            message = str(record.msg)
        record.msg = redact(message)
        record.args = ()
        if record.exc_info:
            # Traceback metni de maskelenir
            record.exc_text = redact(logging.Formatter().formatException(record.exc_info))
            record.exc_info = None
        return True


def setup_logging(level: int = logging.INFO, to_file: bool = True) -> logging.Logger:
    logger = logging.getLogger("aitranslator")
    if getattr(logger, "_configured", False):
        return logger
    logger.setLevel(level)
    logger.propagate = False
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if to_file:
        try:
            handlers.append(RotatingFileHandler(log_path(), maxBytes=512_000, backupCount=2, encoding="utf-8"))
        except OSError:
            pass
    for handler in handlers:
        handler.setFormatter(fmt)
        handler.addFilter(RedactingFilter())
        logger.addHandler(handler)
    logger._configured = True  # type: ignore[attr-defined]
    return logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"aitranslator.{name}")
