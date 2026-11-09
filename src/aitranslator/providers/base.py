"""ProviderInterface: tüm çeviri sağlayıcılarının ortak arayüzü."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

import httpx

from ..secure_storage import SecureStorage
from ..settings import Settings


class ProviderError(Exception):
    """Kullanıcıya gösterilebilir, anlaşılır mesaj taşıyan sağlayıcı hatası.

    kind: config | unreachable | timeout | auth | quota | model_missing | bad_response | blocked
    """

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message


class ProviderInterface(ABC):
    id: str = ""
    label: str = ""
    #: Metin bu sağlayıcıda bilgisayardan dışarı çıkar mı? (Gizlilik bilgilendirmesi için)
    sends_text_offsite: bool = True

    def __init__(self, get_settings: Callable[[], Settings], secrets: SecureStorage) -> None:
        self._get_settings = get_settings
        self._secrets = secrets
        #: Testlerde httpx.MockTransport verilebilir
        self.transport: httpx.BaseTransport | None = None

    # ---- ortak yardımcılar ------------------------------------------------
    @property
    def settings(self) -> Settings:
        return self._get_settings()

    def client(self) -> httpx.Client:
        timeout = max(3, self.settings.providers.timeout_seconds)
        return httpx.Client(timeout=timeout, transport=self.transport, follow_redirects=False)

    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Ağ hatalarını ProviderError'a çevirir."""
        try:
            with self.client() as client:
                return client.request(method, url, **kwargs)
        except httpx.TimeoutException as exc:
            raise ProviderError("timeout", f"{self.label}: yanıt zaman aşımına uğradı.") from exc
        except httpx.ConnectError as exc:
            raise ProviderError("unreachable", self._unreachable_message()) from exc
        except httpx.HTTPError as exc:
            raise ProviderError("unreachable", f"{self.label}: ağ hatası ({type(exc).__name__}).") from exc

    def _unreachable_message(self) -> str:
        return f"{self.label}: sunucuya ulaşılamadı. İnternet/sunucu bağlantısını kontrol edin."

    # ---- arayüz ------------------------------------------------------------
    @abstractmethod
    def is_configured(self) -> bool:
        """Sağlayıcı kullanılabilir şekilde yapılandırılmış mı?"""

    @abstractmethod
    def translate(self, text: str, target: str, source: str = "auto", prompt: str = "") -> str:
        """Metni çevirir; hata durumunda ProviderError fırlatır."""

    @abstractmethod
    def test_connection(self) -> str:
        """Bağlantıyı sınar. Başarılıysa kısa bir bilgi mesajı döner, aksi hâlde ProviderError."""

    def list_models(self) -> list[str]:
        return []

    def privacy_note(self) -> str:
        if self.sends_text_offsite:
            return f"{self.label} kullanılırken çevrilen metin internet üzerinden ilgili servise gönderilir."
        return f"{self.label} kullanılırken metin yalnızca kendi bilgisayarınızdaki/ağınızdaki sunucuya gönderilir."
