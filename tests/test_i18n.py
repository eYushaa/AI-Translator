import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from aitranslator.context import AppContext
from aitranslator.history import HistoryStore
from aitranslator.i18n import (
    SUPPORTED_UI_LANG_CODES,
    TRANSLATIONS,
    UI_LANGUAGES,
    get_ui_language,
    is_rtl,
    normalize_ui_lang,
    provider_label,
    set_ui_language,
    t,
)
from aitranslator.languages import LanguageService
from aitranslator.settings import SettingsManager
from aitranslator.translation_service import TranslationService
from aitranslator.ui.language_picker import LanguagePickerWindow
from aitranslator.ui.popup import TranslationPopup
from aitranslator.ui.settings_window import SettingsWindow
from aitranslator.ui.theme import make_app_icon
from aitranslator.ui.tray import NotificationService, TrayManager


def test_supported_languages_list():
    codes = [code for code, _, _ in UI_LANGUAGES]
    expected = ["tr", "en", "fr", "de", "ru", "ar", "zh-CN", "ja", "ko", "es"]
    assert codes == expected
    for exp in expected:
        assert exp in SUPPORTED_UI_LANG_CODES


def test_normalize_ui_lang():
    assert normalize_ui_lang("en") == "en"
    assert normalize_ui_lang("FR") == "fr"
    assert normalize_ui_lang("de-DE") == "de"
    assert normalize_ui_lang("ru_RU") == "ru"
    assert normalize_ui_lang("ar") == "ar"
    assert normalize_ui_lang("zh") == "zh-CN"
    assert normalize_ui_lang("zh-cn") == "zh-CN"
    assert normalize_ui_lang("ja") == "ja"
    assert normalize_ui_lang("ko") == "ko"
    assert normalize_ui_lang("es") == "es"
    assert normalize_ui_lang("unknown_xyz") == "tr"
    assert normalize_ui_lang("") == "tr"


def test_is_rtl():
    assert is_rtl("ar") is True
    assert is_rtl("en") is False
    assert is_rtl("tr") is False
    assert is_rtl("zh-CN") is False


def test_translations_dictionary_keys():
    tr_keys = set(TRANSLATIONS["tr"].keys())
    for lang_code in ("en", "fr", "de", "ru", "ar", "zh-CN", "ja", "ko", "es"):
        lang_keys = set(TRANSLATIONS[lang_code].keys())
        missing = tr_keys - lang_keys
        assert not missing, f"Language {lang_code} missing keys: {missing}"


def test_language_page_labels_have_clean_tips_without_parentheses():
    for lang_code in ("tr", "en", "fr", "de", "ru", "ar", "zh-CN", "ja", "ko", "es"):
        d = TRANSLATIONS[lang_code]
        assert "(" not in d["lbl_pref_lang"] and ")" not in d["lbl_pref_lang"]
        assert "(" not in d["lbl_alt_b_lang"] and ")" not in d["lbl_alt_b_lang"]
        assert "(" not in d["lbl_alt_n_lang"] and ")" not in d["lbl_alt_n_lang"]
        assert "lbl_pref_lang_tip" in d and len(d["lbl_pref_lang_tip"]) > 0
        assert "lbl_alt_b_lang_tip" in d and len(d["lbl_alt_b_lang_tip"]) > 0
        assert "lbl_alt_n_lang_tip" in d and len(d["lbl_alt_n_lang_tip"]) > 0
        assert "lbl_src_lang_tip" in d and len(d["lbl_src_lang_tip"]) > 0


def test_t_function_and_switching():
    set_ui_language("tr")
    assert t("page_general") == "Genel"

    set_ui_language("en")
    assert t("page_general") == "General"

    set_ui_language("fr")
    assert t("page_general") == "Général"

    set_ui_language("de")
    assert t("page_general") == "Allgemein"

    set_ui_language("ru")
    assert t("page_general") == "Общие"

    set_ui_language("ar")
    assert t("page_general") == "عام"

    set_ui_language("zh-CN")
    assert t("page_general") == "常规"

    set_ui_language("ja")
    assert t("page_general") == "一般"

    set_ui_language("ko")
    assert t("page_general") == "일반"

    set_ui_language("es")
    assert t("page_general") == "General"

    # Reset back to Turkish
    set_ui_language("tr")


def test_settings_ui_language_persistence(tmp_path):
    p = tmp_path / "s.json"
    mgr = SettingsManager(p)
    assert mgr.settings.general.ui_language == "tr"

    mgr.settings.general.ui_language = "de"
    mgr.save()

    mgr2 = SettingsManager(p)
    assert mgr2.settings.general.ui_language == "de"
    assert get_ui_language() == "de"

    # Clean up
    set_ui_language("tr")


def test_settings_window_language_switching(settings, secrets, tmp_path):
    app = QApplication.instance() or QApplication([])
    history = HistoryStore(tmp_path / "h.jsonl")
    translation = TranslationService(settings, secrets, providers={})
    ctx = AppContext(settings, secrets, translation, history, None, lambda: {}, {})
    win = SettingsWindow(ctx, make_app_icon())

    # Initial state (default: tr)
    assert win.sidebar.item(0).text() == "Genel"
    assert win.save_btn.text() == "Kaydet"
    assert win.layoutDirection() == Qt.LayoutDirection.LeftToRight

    # Switch to English in UI
    en_idx = win.cmb_ui_lang.findData("en")
    assert en_idx >= 0
    win.cmb_ui_lang.setCurrentIndex(en_idx)
    assert win.sidebar.item(0).text() == "General"
    assert win.save_btn.text() == "Save"
    assert win.layoutDirection() == Qt.LayoutDirection.LeftToRight

    # Switch to Arabic in UI (checks RTL)
    ar_idx = win.cmb_ui_lang.findData("ar")
    assert ar_idx >= 0
    win.cmb_ui_lang.setCurrentIndex(ar_idx)
    assert win.sidebar.item(0).text() == "عام"
    assert win.save_btn.text() == "حفظ"
    assert win.layoutDirection() == Qt.LayoutDirection.RightToLeft

    # Switch to Russian in UI
    ru_idx = win.cmb_ui_lang.findData("ru")
    assert ru_idx >= 0
    win.cmb_ui_lang.setCurrentIndex(ru_idx)
    assert win.sidebar.item(0).text() == "Общие"
    assert win.save_btn.text() == "Сохранить"

    # Switch to Chinese (zh-CN) in UI
    zh_idx = win.cmb_ui_lang.findData("zh-CN")
    assert zh_idx >= 0
    win.cmb_ui_lang.setCurrentIndex(zh_idx)
    assert win.sidebar.item(0).text() == "常规"
    assert win.save_btn.text() == "保存"

    # Switch to Japanese in UI
    ja_idx = win.cmb_ui_lang.findData("ja")
    assert ja_idx >= 0
    win.cmb_ui_lang.setCurrentIndex(ja_idx)
    assert win.sidebar.item(0).text() == "一般"
    assert win.save_btn.text() == "保存"

    # Switch to Korean in UI
    ko_idx = win.cmb_ui_lang.findData("ko")
    assert ko_idx >= 0
    win.cmb_ui_lang.setCurrentIndex(ko_idx)
    assert win.sidebar.item(0).text() == "일반"
    assert win.save_btn.text() == "저장"

    # Switch to Spanish in UI
    es_idx = win.cmb_ui_lang.findData("es")
    assert es_idx >= 0
    win.cmb_ui_lang.setCurrentIndex(es_idx)
    assert win.sidebar.item(0).text() == "General"
    assert win.save_btn.text() == "Guardar"

    # Save while Spanish is selected
    win.save()
    assert settings.settings.general.ui_language == "es"

    # Reset back to Turkish
    tr_idx = win.cmb_ui_lang.findData("tr")
    win.cmb_ui_lang.setCurrentIndex(tr_idx)
    win.save()
    assert settings.settings.general.ui_language == "tr"


def test_tray_manager_retranslate(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(TrayManager, "available", lambda: True)
    notifier = NotificationService()
    icon = make_app_icon(32)

    set_ui_language("tr")
    tray = TrayManager(icon, False, True, notifier)
    assert tray.act_settings.text() == "Ayarlar"
    assert tray.act_quit.text() == "Çıkış"

    set_ui_language("en")
    tray.retranslate()
    assert tray.act_settings.text() == "Settings"
    assert tray.act_quit.text() == "Quit"

    set_ui_language("de")
    tray.retranslate()
    assert tray.act_settings.text() == "Einstellungen"
    assert tray.act_quit.text() == "Beenden"

    set_ui_language("fr")
    tray.retranslate()
    assert tray.act_settings.text() == "Paramètres"
    assert tray.act_quit.text() == "Quitter"

    set_ui_language("ru")
    tray.retranslate()
    assert tray.act_settings.text() == "Настройки"
    assert tray.act_quit.text() == "Выход"

    set_ui_language("ar")
    tray.retranslate()
    assert tray.act_settings.text() == "الإعدادات"
    assert tray.act_quit.text() == "خروج"

    set_ui_language("zh-CN")
    tray.retranslate()
    assert tray.act_settings.text() == "设置"
    assert tray.act_quit.text() == "退出"

    set_ui_language("ja")
    tray.retranslate()
    assert tray.act_settings.text() == "設定"
    assert tray.act_quit.text() == "終了"

    set_ui_language("ko")
    tray.retranslate()
    assert tray.act_settings.text() == "설정"
    assert tray.act_quit.text() == "종료"

    set_ui_language("es")
    tray.retranslate()
    assert tray.act_settings.text() == "Configuración"
    assert tray.act_quit.text() == "Salir"

    # Reset
    set_ui_language("tr")


def test_popup_and_picker_language_retranslate(tmp_path):
    app = QApplication.instance() or QApplication([])
    p = tmp_path / "s.json"
    mgr = SettingsManager(p)

    set_ui_language("ar")
    picker = LanguagePickerWindow(mgr, lambda t, m, l: None)
    picker.open_picker()
    assert picker.layoutDirection() == Qt.LayoutDirection.RightToLeft
    assert "🌐" in picker.lbl_title.text()
    assert picker.btn_select.text() == "اختيار"
    picker.hide()

    popup = TranslationPopup()
    popup.display("Hello", "مرحبا", "ar", "Google")
    assert popup.layoutDirection() == Qt.LayoutDirection.RightToLeft
    assert popup.btn_copy.text() == "📋 نسخ"
    assert popup.btn_dismiss.text() == "إغلاق"
    popup.hide()

    set_ui_language("tr")

