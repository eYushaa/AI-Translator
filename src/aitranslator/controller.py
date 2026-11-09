"""TranslationController: kısayol → seçim al → çevir → yerine yaz akışını yönetir (Qt'den bağımsız)."""
from __future__ import annotations

import threading
import time
from typing import Callable

from .errors import ReplacementError, SelectionError
from .history import HistoryStore
from .i18n import t
from .languages import LanguageService
from .logging_service import get_logger
from .ocr import OcrService
from .providers import GRAMMAR_FIX_PROMPT, IMPROVE_TEXT_PROMPT
from .replacement import TextReplacementService
from .selection import TextSelectionService
from .settings import SettingsManager
from .translation_service import TranslationError, TranslationService

log = get_logger("controller")

#: notify(başlık, mesaj, düzey) ; düzey: "info" | "error"
Notify = Callable[[str, str, str], None]
#: show_popup(orijinal, çeviri, hedef_dil, sağlayıcı_adı, [konum])
ShowPopup = Callable[..., None]

BUSY_NOTICE_DELAY = 1.2  # saniye – hızlı çeviride gereksiz bildirim göstermemek için


class TranslationController:
    def __init__(
        self,
        settings: SettingsManager,
        translation: TranslationService,
        selection: TextSelectionService,
        replacement: TextReplacementService,
        history: HistoryStore,
        notify: Notify,
        show_popup: ShowPopup | None = None,
        show_language_picker: Callable[[], None] | None = None,
        request_ocr: Callable[[], None] | None = None,
        ocr_service: OcrService | None = None,
    ) -> None:
        self._settings = settings
        self._translation = translation
        self._selection = selection
        self._replacement = replacement
        self._history = history
        self._notify = notify
        self._show_popup = show_popup
        self._show_language_picker = show_language_picker
        self._request_ocr = request_ocr
        self._ocr = ocr_service or OcrService(gemini_provider=translation.providers.get("gemini"))
        self._busy = threading.Lock()
        self.last_translation: str = ""

    # Kısayol iş parçacığını bloke etmemek için ayrı iş parçacığında çalıştırılır
    def handle_hotkey(self, name: str) -> None:
        if name == "alt_m":
            if self._show_language_picker:
                self._show_language_picker()
            return
        if name == "alt_o":
            if self._request_ocr:
                self._request_ocr()
            return
        threading.Thread(target=self.run_job, args=(name,), name=f"Translate-{name}", daemon=True).start()

    def run_job(self, hotkey_name: str) -> bool:
        """Bir çeviri veya metin düzenleme işini eşzamanlı çalıştırır. Başarılıysa True."""
        if hotkey_name == "alt_m":
            if self._show_language_picker:
                self._show_language_picker()
                return True
            return False
        if hotkey_name == "alt_o":
            if self._request_ocr:
                self._request_ocr()
                return True
            return False
        if not self._busy.acquire(blocking=False):
            self._notify(t("notify_busy_prev_title"), t("notify_busy_prev_msg"), "info")
            return False
        timer: threading.Timer | None = None
        try:
            s = self._settings.settings
            selection = self._selection.capture()

            prompt_override: str | None = None
            if hotkey_name == "alt_v":
                prompt_override = IMPROVE_TEXT_PROMPT
                target = LanguageService.guess_language(selection.text)
                busy_title, busy_text = t("notify_improving_title"), t("notify_improving_msg")
                done_title = t("notify_improved_title")
            elif hotkey_name == "alt_c":
                prompt_override = GRAMMAR_FIX_PROMPT
                target = LanguageService.guess_language(selection.text)
                busy_title, busy_text = t("notify_grammar_title"), t("notify_grammar_msg")
                done_title = t("notify_grammar_done_title")
            else:
                target = s.target_for(hotkey_name)
                tgt_name = LanguageService.display_name(target)
                busy_title, busy_text = t("notify_translating_title"), t("notify_translating_msg", target=tgt_name)
                done_title = t("notify_translated_title")

            timer = threading.Timer(BUSY_NOTICE_DELAY, self._notify, (busy_title, busy_text, "info"))
            timer.daemon = True
            timer.start()

            result = self._translation.translate(selection.text, target, prompt_override=prompt_override)
            self.last_translation = result.text
            timer.cancel()

            if hotkey_name == "alt_n":
                # Alt+N: Metni yerinde değiştirmek yerine kutucukta göster
                if self._show_popup:
                    self._show_popup(selection.text, result.text, target, result.provider_label)
            else:
                # Alt+B, Alt+V, Alt+C: Metni yerinde değiştir (başarısız olursa kutucukta göster)
                try:
                    self._replacement.replace(selection, result.text)
                except ReplacementError:
                    if self._show_popup:
                        self._show_popup(selection.text, result.text, target, result.provider_label)
                    raise

            if s.privacy.history_enabled:
                try:
                    hist_target = "improve" if hotkey_name == "alt_v" else ("grammar" if hotkey_name == "alt_c" else target)
                    self._history.add(selection.text, result.text, hist_target, result.provider_id)
                except OSError:
                    log.warning("Geçmişe yazılamadı")

            if s.general.notify_on_done:
                time_str = t("notify_from_cache") if result.from_cache else t("notify_seconds", seconds=result.seconds)
                if hotkey_name == "alt_v":
                    done_desc = t("notify_improved_desc", provider=result.provider_label, time_str=time_str)
                elif hotkey_name == "alt_c":
                    done_desc = t("notify_grammar_done_desc", provider=result.provider_label, time_str=time_str)
                else:
                    src = LanguageService.display_name(LanguageService.guess_language(selection.text))
                    auto_label = t("auto_detect")
                    done_desc = (
                        f"{result.provider_label} • {LanguageService.display_name(target)}"
                        + time_str
                        + (t("notify_source_line", src=src) if src != auto_label and src != "Otomatik algıla" else "")
                    )
                self._notify(done_title, done_desc, "info")
            return True
        except SelectionError as exc:
            self._notify(t("notify_err_selection"), exc.message, "error")
        except TranslationError as exc:
            self._notify(t("notify_err_translation"), exc.message, "error")
        except ReplacementError as exc:
            self._notify(t("notify_err_replacement"), exc.message + t("notify_err_replacement_hint"), "error")
        except Exception:  # noqa: BLE001 - hiçbir hata kullanıcının metnini etkilememeli
            log.exception("Beklenmeyen hata")
            self._notify(t("notify_err_unexpected_title"), t("notify_err_unexpected_msg"), "error")
        finally:
            if timer:
                timer.cancel()
            self._busy.release()
        return False

    def process_ocr_image(self, image: Any, pos: Any = None) -> None:
        """Kırpılan ekran görüntüsünü arka planda OCR ve çeviri işlemine alır."""
        threading.Thread(target=self._run_ocr_job, args=(image, pos), name="Translate-OCR", daemon=True).start()

    def _run_ocr_job(self, image: Any, pos: Any = None) -> bool:
        if not self._busy.acquire(blocking=False):
            self._notify(t("notify_busy_prev_title"), t("notify_busy_prev_msg"), "info")
            return False
        timer: threading.Timer | None = None
        try:
            s = self._settings.settings
            target = s.target_for("alt_o")
            ocr_cfg = getattr(s, "ocr", None)
            engine = ocr_cfg.engine if ocr_cfg else "auto"
            fallback = ocr_cfg.fallback_to_ai if ocr_cfg else True
            show_notify = ocr_cfg.show_notification if ocr_cfg else True

            if show_notify:
                self._notify(t("ocr_reading_title"), t("ocr_reading_msg"), "info")

            # 1. OCR ile metni çıkar
            extracted = self._ocr.extract_text(image, engine=engine, fallback_to_ai=fallback)
            if not extracted or not extracted.strip():
                self._notify(t("ocr_empty_title"), t("ocr_empty_msg"), "error")
                return False

            if ocr_cfg and ocr_cfg.copy_to_clipboard:
                try:
                    from PySide6.QtGui import QGuiApplication
                    cb = QGuiApplication.clipboard()
                    if cb:
                        cb.setText(extracted)
                except Exception:
                    log.warning("Pano kopyalama hatası")

            if show_notify:
                timer = threading.Timer(
                    BUSY_NOTICE_DELAY,
                    self._notify,
                    (t("notify_translating_title"), t("notify_translating_msg", target=LanguageService.display_name(target)), "info"),
                )
                timer.daemon = True
                timer.start()

            # 2. Metni hedef dile çevir
            result = self._translation.translate(extracted, target)
            self.last_translation = result.text
            if timer:
                timer.cancel()

            # 3. Sonucu kutucukta göster
            if self._show_popup:
                self._show_popup(extracted, result.text, target, f"OCR • {result.provider_label}", pos)

            if s.privacy.history_enabled:
                try:
                    self._history.add(extracted, result.text, f"ocr->{target}", result.provider_id)
                except OSError:
                    log.warning("Geçmişe yazılamadı")

            if s.general.notify_on_done and show_notify:
                time_str = t("notify_from_cache") if result.from_cache else t("notify_seconds", seconds=result.seconds)
                self._notify(
                    t("ocr_done_title"),
                    f"{result.provider_label} • {LanguageService.display_name(target)}{time_str}",
                    "info",
                )
            return True
        except TranslationError as exc:
            self._notify(t("notify_err_translation"), exc.message, "error")
        except Exception:  # noqa: BLE001
            log.exception("OCR işlem hatası")
            self._notify(t("notify_err_unexpected_title"), t("notify_err_unexpected_msg"), "error")
        finally:
            if timer:
                timer.cancel()
            self._busy.release()
        return False
