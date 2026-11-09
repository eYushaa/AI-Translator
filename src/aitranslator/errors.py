"""Kullanıcıya doğrudan gösterilebilecek mesajlar taşıyan hata türleri."""
from __future__ import annotations


class UserFacingError(Exception):
    """``message`` doğrudan bildirimde gösterilir."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class SelectionError(UserFacingError):
    """Seçili metin alınamadı / alanda güvenle çalışılamıyor."""


class ReplacementError(UserFacingError):
    """Çeviri hedef alana güvenle yazılamadı (orijinal metne dokunulmadı)."""
