"""SecureStorage: API anahtarlarını düz metin dosyalarda tutmadan saklar.

Öncelik sırası:
1. Windows Credential Manager (``keyring`` üzerinden)
2. Windows DPAPI ile şifrelenmiş dosya (yalnızca aynı Windows kullanıcısı çözebilir)
3. Bellek (yalnızca testler / desteklenmeyen platformlar; kalıcı değildir)
"""
from __future__ import annotations

import base64
import json
import sys
from typing import Protocol

from . import APP_NAME
from .logging_service import get_logger
from .paths import secrets_path

log = get_logger("secrets")


class SecretBackend(Protocol):
    def get(self, name: str) -> str | None: ...
    def set(self, name: str, value: str) -> None: ...
    def delete(self, name: str) -> None: ...


class MemoryBackend:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}
        self.persistent = False

    def get(self, name: str) -> str | None:
        return self._data.get(name)

    def set(self, name: str, value: str) -> None:
        self._data[name] = value

    def delete(self, name: str) -> None:
        self._data.pop(name, None)


class KeyringBackend:
    persistent = True

    def __init__(self) -> None:
        import keyring  # noqa: PLC0415 - isteğe bağlı bağımlılık
        from keyring.backends.fail import Keyring as FailKeyring

        self._kr = keyring
        if isinstance(keyring.get_keyring(), FailKeyring):
            raise RuntimeError("Kullanılabilir keyring arka ucu yok")

    def get(self, name: str) -> str | None:
        return self._kr.get_password(APP_NAME, name)

    def set(self, name: str, value: str) -> None:
        self._kr.set_password(APP_NAME, name, value)

    def delete(self, name: str) -> None:
        try:
            self._kr.delete_password(APP_NAME, name)
        except Exception:  # noqa: BLE001 - yoksa sorun değil
            pass


class DpapiFileBackend:
    """Windows DPAPI (CryptProtectData) ile şifrelenmiş JSON dosyası."""

    persistent = True

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError("DPAPI yalnızca Windows'ta kullanılabilir")
        self.path = secrets_path()

    # --- DPAPI çağrıları -------------------------------------------------
    @staticmethod
    def _blob(data: bytes):
        import ctypes
        from ctypes import wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

        buf = ctypes.create_string_buffer(data, len(data))
        return DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf, DATA_BLOB

    def _protect(self, raw: bytes, encrypt: bool) -> bytes:
        import ctypes

        blob_in, _keep, blob_type = self._blob(raw)
        blob_out = blob_type()
        crypt32 = ctypes.windll.crypt32  # type: ignore[attr-defined]
        fn = crypt32.CryptProtectData if encrypt else crypt32.CryptUnprotectData
        args = (ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out))
        if not fn(*args):
            raise OSError("DPAPI işlemi başarısız")
        try:
            return ctypes.string_at(blob_out.pbData, blob_out.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)  # type: ignore[attr-defined]

    # --- Dosya işlemleri -------------------------------------------------
    def _read(self) -> dict[str, str]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _write(self, data: dict[str, str]) -> None:
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def get(self, name: str) -> str | None:
        enc = self._read().get(name)
        if not enc:
            return None
        try:
            return self._protect(base64.b64decode(enc), encrypt=False).decode("utf-8")
        except (OSError, ValueError):
            return None

    def set(self, name: str, value: str) -> None:
        data = self._read()
        data[name] = base64.b64encode(self._protect(value.encode("utf-8"), encrypt=True)).decode("ascii")
        self._write(data)

    def delete(self, name: str) -> None:
        data = self._read()
        if data.pop(name, None) is not None:
            self._write(data)


class SecureStorage:
    KNOWN = ("gemini_api_key", "lmstudio_api_key", "local_llm_api_key", "google_cloud_api_key")

    def __init__(self, backend: SecretBackend | None = None) -> None:
        self.backend: SecretBackend = backend or self._auto_backend()
        self.persistent = getattr(self.backend, "persistent", True)

    @staticmethod
    def _auto_backend() -> SecretBackend:
        for factory in (KeyringBackend, DpapiFileBackend):
            try:
                return factory()
            except Exception as exc:  # noqa: BLE001
                log.info("Gizli depo arka ucu kullanılamadı: %s", type(exc).__name__)
        log.warning("Kalıcı güvenli depo yok; anahtarlar yalnızca bu oturumda tutulacak")
        return MemoryBackend()

    def get(self, name: str) -> str:
        try:
            return self.backend.get(name) or ""
        except Exception as exc:  # noqa: BLE001
            log.warning("Gizli depo okuma hatası: %s", type(exc).__name__)
            return ""

    def set(self, name: str, value: str) -> None:
        if value:
            self.backend.set(name, value)
        else:
            self.backend.delete(name)

    def has(self, name: str) -> bool:
        return bool(self.get(name))
