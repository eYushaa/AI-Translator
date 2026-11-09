"""Ayarlar penceresi: Genel, Diller, Sağlayıcılar, Kısayollar, Gizlilik, Geçmiş."""
from __future__ import annotations

import copy
import threading
import time

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QListWidget, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QStackedWidget, QTableWidget,
    QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget, QKeySequenceEdit,
)

from .. import APP_NAME, __version__, autostart
from ..context import AppContext
from ..i18n import (
    UI_LANGUAGES, get_ui_language, is_rtl, provider_label, set_ui_language, t,
)
from ..languages import LanguageService
from ..ocr import OcrService
from ..paths import data_dir, history_path, log_path
from ..providers import (
    DEFAULT_SYSTEM_PROMPT, GeminiProvider, GoogleTranslateProvider, LMStudioProvider, LocalLLMProvider,
    PROMPT_PRESETS, ProviderError,
)
from ..secure_storage import MemoryBackend, SecureStorage
from ..settings import OcrSettings, PROVIDER_IDS, PROVIDER_LABELS, Settings
from ..winplat.hotkey_parse import find_duplicates
from .widgets import Card, LanguageCombo, muted_label, primary_button, secret_edit, title_label

PAGE_KEYS = ["page_general", "page_languages", "page_ocr", "page_providers", "page_hotkeys", "page_privacy", "page_history"]
PAGES = ["Genel", "Diller", "OCR / Ekran Alıntısı", "Sağlayıcılar", "Kısayollar", "Gizlilik", "Geçmiş"]
SECRET_FOR = {"local_llm": "local_llm_api_key", "lmstudio": "lmstudio_api_key", "gemini": "gemini_api_key", "google": "google_cloud_api_key"}
PROVIDER_CLASSES = {"local_llm": LocalLLMProvider, "lmstudio": LMStudioProvider, "gemini": GeminiProvider, "google": GoogleTranslateProvider}
GEMINI_SUGGESTIONS = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"]


def _scroll(inner: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(inner)
    return area


class SettingsWindow(QMainWindow):
    test_finished = Signal(str, bool, str)
    models_loaded = Signal(str, list, str)
    ui_language_changed = Signal(str)

    def __init__(self, ctx: AppContext, icon) -> None:
        super().__init__()
        self.ctx = ctx
        self.really_quit = False
        self._delete_secrets: set[str] = set()
        self._page_headers: list[tuple[QLabel, QLabel | None, str, str]] = []
        self._provider_tab_widgets: list[tuple[str, QLabel, list[QPushButton]]] = []
        self._key_rows: list[tuple[str, QLabel, QLineEdit, QPushButton]] = []

        self.setWindowTitle(t("window_title", app_name=APP_NAME))
        self.setWindowIcon(icon)
        self.resize(960, 680)

        # Sol Panel: Üstte menü listesi, en altta uygulama dili değiştirme çubuğu
        self.left_panel = QWidget()
        self.left_panel.setObjectName("LeftPanel")
        self.left_panel.setFixedWidth(220)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("Sidebar")
        for key in PAGE_KEYS:
            self.sidebar.addItem(t(key))
        left_layout.addWidget(self.sidebar, 1)

        # En alttaki uygulama dili çubuğu (Bottom Language Bar)
        self.sidebar_bottom = QWidget()
        self.sidebar_bottom.setObjectName("SidebarBottom")
        bottom_layout = QVBoxLayout(self.sidebar_bottom)
        bottom_layout.setContentsMargins(12, 10, 12, 14)
        bottom_layout.setSpacing(6)

        self.lbl_ui_lang = QLabel(f"🌐  {t('lbl_ui_language')}")
        self.lbl_ui_lang.setStyleSheet("font-weight: 600; font-size: 9pt;")
        bottom_layout.addWidget(self.lbl_ui_lang)

        self.cmb_ui_lang = QComboBox()
        self.cmb_ui_lang.setObjectName("LanguageBar")
        for code, native, tr_name in UI_LANGUAGES:
            disp = f"{native} ({tr_name})" if native != tr_name else native
            self.cmb_ui_lang.addItem(disp, code)
        self.cmb_ui_lang.currentIndexChanged.connect(self._on_ui_language_selected)
        bottom_layout.addWidget(self.cmb_ui_lang)

        left_layout.addWidget(self.sidebar_bottom)

        self.stack = QStackedWidget()
        for builder in (
            self._build_general,
            self._build_languages,
            self._build_ocr,
            self._build_providers,
            self._build_hotkeys,
            self._build_privacy,
            self._build_history,
        ):
            self.stack.addWidget(builder())
        self.sidebar.currentRowChanged.connect(self._on_page_changed)

        self.status = QLabel("")
        self.status.setObjectName("Subtle")
        self.save_btn = primary_button(t("btn_save"))
        self.save_btn.clicked.connect(self.save)
        bar = QHBoxLayout()
        bar.setContentsMargins(28, 10, 28, 14)
        bar.addWidget(self.status, 1)
        bar.addWidget(self.save_btn)
        right = QWidget()
        right.setObjectName("Root")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        rl.addWidget(self.stack, 1)
        rl.addLayout(bar)

        root = QWidget()
        hl = QHBoxLayout(root)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)
        hl.addWidget(self.left_panel)
        hl.addWidget(right, 1)
        self.setCentralWidget(root)

        self.test_finished.connect(self._on_test_finished)
        self.models_loaded.connect(self._on_models_loaded)
        self.load_from_settings()
        self.sidebar.setCurrentRow(0)

    def _page(self, title_key: str, subtitle_key: str = "") -> tuple[QWidget, QVBoxLayout]:
        w = QWidget()
        w.setObjectName("Root")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)
        tl = title_label(t(title_key))
        lay.addWidget(tl)
        sub = muted_label(t(subtitle_key)) if subtitle_key else None
        if sub:
            lay.addWidget(sub)
        self._page_headers.append((tl, sub, title_key, subtitle_key))
        return w, lay

    # ================= sayfalar =================
    def _build_general(self) -> QWidget:
        page, lay = self._page("page_general", "general_subtitle")
        card = Card()

        self.chk_autostart = QCheckBox(t("chk_autostart"))
        self.chk_tray = QCheckBox(t("chk_tray"))
        self.chk_notify = QCheckBox(t("chk_notify"))
        self.chk_autodetect = QCheckBox(t("chk_autodetect"))
        self.chk_keep = QCheckBox(t("chk_keep"))
        self.chk_keep.setEnabled(False)
        for c in (self.chk_autostart, self.chk_tray, self.chk_notify, self.chk_autodetect, self.chk_keep):
            card.root.addWidget(c)
        lay.addWidget(card)

        self.lbl_gen_footer = muted_label(t("general_footer", app_name=APP_NAME, version=__version__))
        lay.addWidget(self.lbl_gen_footer)
        lay.addStretch(1)
        return _scroll(page)

    def _build_languages(self) -> QWidget:
        page, lay = self._page("page_languages", "languages_subtitle")
        card = Card()

        self.cmb_pref = LanguageCombo()
        self.cmb_b = LanguageCombo(extra_first=("", t("use_primary_lang")), extra_first_key="use_primary_lang")
        self.cmb_n = LanguageCombo(extra_first=("", t("use_primary_lang")), extra_first_key="use_primary_lang")
        self.cmb_src = LanguageCombo(include_auto=True)

        self.rows_layout = QVBoxLayout()
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(18)
        self.form_langs = self.rows_layout  # geriye dönük uyumluluk

        def _make_lang_row(title_key: str, tip_key: str, combo: QWidget) -> tuple[QLabel, QLabel]:
            row = QHBoxLayout()
            row.setContentsMargins(0, 2, 0, 2)
            row.setSpacing(24)

            vbox = QVBoxLayout()
            vbox.setContentsMargins(0, 0, 0, 0)
            vbox.setSpacing(3)

            lbl_title = QLabel(t(title_key))
            lbl_title.setStyleSheet("font-weight: 600; font-size: 9.5pt;")
            vbox.addWidget(lbl_title)

            lbl_tip = QLabel(t(tip_key))
            lbl_tip.setObjectName("Subtle")
            lbl_tip.setStyleSheet("font-size: 8.5pt;")
            lbl_tip.setWordWrap(True)
            vbox.addWidget(lbl_tip)

            row.addLayout(vbox, 1)

            combo.setFixedWidth(280)
            row.addWidget(combo, 0, Qt.AlignmentFlag.AlignVCenter)

            self.rows_layout.addLayout(row)
            return lbl_title, lbl_tip

        self.lbl_row_pref, self.lbl_tip_pref = _make_lang_row("lbl_pref_lang", "lbl_pref_lang_tip", self.cmb_pref)
        self.lbl_row_b, self.lbl_tip_b = _make_lang_row("lbl_alt_b_lang", "lbl_alt_b_lang_tip", self.cmb_b)
        self.lbl_row_n, self.lbl_tip_n = _make_lang_row("lbl_alt_n_lang", "lbl_alt_n_lang_tip", self.cmb_n)
        self.lbl_row_src, self.lbl_tip_src = _make_lang_row("lbl_src_lang", "lbl_src_lang_tip", self.cmb_src)

        card.root.addLayout(self.rows_layout)

        card.root.addSpacing(6)
        self.lbl_note_src = QLabel("")
        self.lbl_note_src.setVisible(False)
        self.lbl_note_alt_m = muted_label(t("languages_note_alt_m"))
        self.lbl_note_alt_m.setWordWrap(True)
        self.lbl_note_alt_m.setStyleSheet("font-size: 8.5pt; padding-top: 6px;")
        card.root.addWidget(self.lbl_note_alt_m)
        lay.addWidget(card)

        prompt_card = Card()
        pheader = QHBoxLayout()
        self.lbl_prompt_title = QLabel(t("prompt_header"))
        self.lbl_prompt_title.setStyleSheet("font-weight: 600; font-size: 11pt;")
        pheader.addWidget(self.lbl_prompt_title)
        pheader.addStretch(1)
        prompt_card.root.addLayout(pheader)

        preset_row = QHBoxLayout()
        self.lbl_presets = QLabel(t("lbl_presets"))
        self.lbl_presets.setStyleSheet("font-weight: 500;")
        self.cmb_prompt_presets = QComboBox()
        self._populate_prompt_presets()
        self.cmb_prompt_presets.currentIndexChanged.connect(self._on_prompt_preset_changed)

        self.btn_reset_prompt = QPushButton(t("btn_reset_prompt"))
        self.btn_reset_prompt.clicked.connect(self._reset_prompt)

        preset_row.addWidget(self.lbl_presets)
        preset_row.addWidget(self.cmb_prompt_presets, 1)
        preset_row.addWidget(self.btn_reset_prompt)
        prompt_card.root.addLayout(preset_row)

        self.txt_prompt = QPlainTextEdit()
        self.txt_prompt.setMinimumHeight(150)
        self.txt_prompt.setPlaceholderText(t("prompt_placeholder"))
        self.txt_prompt.textChanged.connect(self._on_prompt_text_changed)
        prompt_card.root.addWidget(self.txt_prompt)

        self.lbl_prompt_help = muted_label(t("prompt_help"))
        prompt_card.root.addWidget(self.lbl_prompt_help)
        lay.addWidget(prompt_card)

        lay.addStretch(1)
        return _scroll(page)

    def _populate_prompt_presets(self) -> None:
        cur_idx = self.cmb_prompt_presets.currentIndex()
        self.cmb_prompt_presets.blockSignals(True)
        self.cmb_prompt_presets.clear()
        self.cmb_prompt_presets.addItem(t("preset_custom"), "")
        for i, (_, tmpl) in enumerate(PROMPT_PRESETS):
            self.cmb_prompt_presets.addItem(t(f"preset_{i}"), tmpl)
        if cur_idx >= 0:
            self.cmb_prompt_presets.setCurrentIndex(min(cur_idx, self.cmb_prompt_presets.count() - 1))
        self.cmb_prompt_presets.blockSignals(False)

    def _on_prompt_preset_changed(self, index: int) -> None:
        tmpl = self.cmb_prompt_presets.itemData(index)
        if tmpl:
            self.txt_prompt.blockSignals(True)
            self.txt_prompt.setPlainText(tmpl)
            self.txt_prompt.blockSignals(False)

    def _on_prompt_text_changed(self) -> None:
        current_text = self.txt_prompt.toPlainText().strip()
        matched = 0
        for i, (_, tmpl) in enumerate(PROMPT_PRESETS, start=1):
            if current_text == tmpl.strip():
                matched = i
                break
        self.cmb_prompt_presets.blockSignals(True)
        self.cmb_prompt_presets.setCurrentIndex(matched)
        self.cmb_prompt_presets.blockSignals(False)

    def _reset_prompt(self) -> None:
        self.cmb_prompt_presets.blockSignals(True)
        self.cmb_prompt_presets.setCurrentIndex(1)  # Doğal / Standart Çeviri
        self.cmb_prompt_presets.blockSignals(False)
        self.txt_prompt.setPlainText(DEFAULT_SYSTEM_PROMPT)

    def _build_ocr(self) -> QWidget:
        page, lay = self._page("page_ocr", "ocr_subtitle")

        # 1. OCR Motoru ve Çeviri Ayarları Kartı
        card_engine = Card()
        form = QFormLayout()
        form.setVerticalSpacing(12)
        form.setHorizontalSpacing(16)

        self.lbl_ocr_engine = QLabel(t("ocr_engine_label"))
        self.lbl_ocr_engine.setStyleSheet("font-weight: 600;")
        self.cmb_ocr_engine = QComboBox()
        self.cmb_ocr_engine.addItem(t("ocr_engine_auto"), "auto")
        self.cmb_ocr_engine.addItem(t("ocr_engine_windows"), "windows")
        self.cmb_ocr_engine.addItem(t("ocr_engine_gemini"), "gemini")
        form.addRow(self.lbl_ocr_engine, self.cmb_ocr_engine)

        self.lbl_ocr_target = QLabel(t("ocr_target_lang_label"))
        self.lbl_ocr_target.setStyleSheet("font-weight: 600;")
        self.cmb_ocr_target = LanguageCombo(
            extra_first=("", t("ocr_target_lang_default")),
            extra_first_key="ocr_target_lang_default",
            include_auto=False,
        )
        form.addRow(self.lbl_ocr_target, self.cmb_ocr_target)

        card_engine.root.addLayout(form)

        self.chk_ocr_fallback = QCheckBox(t("ocr_chk_fallback"))
        self.chk_ocr_clipboard = QCheckBox(t("ocr_chk_clipboard"))
        self.chk_ocr_notify = QCheckBox(t("ocr_chk_notify"))

        card_engine.root.addWidget(self.chk_ocr_fallback)
        card_engine.root.addWidget(self.chk_ocr_clipboard)
        card_engine.root.addWidget(self.chk_ocr_notify)
        lay.addWidget(card_engine)

        # 2. Windows Yerel OCR Durumu Kartı
        card_winocr = Card()
        self.lbl_winocr_title = QLabel(t("ocr_installed_langs_title"))
        self.lbl_winocr_title.setStyleSheet("font-weight: 600; font-size: 11pt;")
        card_winocr.root.addWidget(self.lbl_winocr_title)

        installed_langs = OcrService.get_installed_windows_ocr_languages()
        if installed_langs:
            txt = t("ocr_installed_langs_detected", langs=", ".join(installed_langs))
            self.lbl_winocr_status = QLabel(txt)
            self.lbl_winocr_status.setStyleSheet("color: #1E8E5A; font-weight: 500;")
        else:
            self.lbl_winocr_status = QLabel(t("ocr_no_installed_langs"))
            self.lbl_winocr_status.setStyleSheet("color: #C77700;")
        self.lbl_winocr_status.setWordWrap(True)
        card_winocr.root.addWidget(self.lbl_winocr_status)
        lay.addWidget(card_winocr)

        # 3. Nasıl Kullanılır? & Kısayol Kartı
        card_help = Card()
        self.lbl_ocr_help_title = QLabel(t("ocr_how_to_use_title"))
        self.lbl_ocr_help_title.setStyleSheet("font-weight: 600; font-size: 11pt;")
        card_help.root.addWidget(self.lbl_ocr_help_title)

        self.lbl_ocr_help_desc = QLabel()
        self.lbl_ocr_help_desc.setWordWrap(True)
        self.lbl_ocr_help_desc.setText(
            t("ocr_how_to_use_desc", hotkey=self.ctx.settings.settings.hotkeys.alt_o)
        )
        card_help.root.addWidget(self.lbl_ocr_help_desc)

        btn_row = QHBoxLayout()
        self.btn_ocr_hotkey = QPushButton(t("ocr_btn_goto_hotkeys"))
        self.btn_ocr_hotkey.clicked.connect(self._goto_hotkeys_page)
        btn_row.addWidget(self.btn_ocr_hotkey)
        btn_row.addStretch(1)
        card_help.root.addLayout(btn_row)

        lay.addWidget(card_help)
        lay.addStretch(1)
        return _scroll(page)

    def _goto_hotkeys_page(self) -> None:
        idx = PAGE_KEYS.index("page_hotkeys")
        self.sidebar.setCurrentRow(idx)

    def _build_providers(self) -> QWidget:
        page, lay = self._page("page_providers", "providers_subtitle")
        top = Card()
        form = QFormLayout()
        self.lbl_active_provider = QLabel(t("lbl_active_provider"))
        self.cmb_active = QComboBox()
        for pid in PROVIDER_IDS:
            self.cmb_active.addItem(provider_label(pid), pid)
        self.cmb_active.currentIndexChanged.connect(self._update_privacy_note)
        form.addRow(self.lbl_active_provider, self.cmb_active)
        top.root.addLayout(form)
        self.lbl_privacy_note = muted_label("")
        top.root.addWidget(self.lbl_privacy_note)
        self.chk_fallback = QCheckBox(t("chk_fallback"))
        top.root.addWidget(self.chk_fallback)
        self.warn_fallback = muted_label(t("providers_fallback_warn"))
        self.warn_fallback.setObjectName("Warn")
        top.root.addWidget(self.warn_fallback)
        lay.addWidget(top)

        self.pw: dict[str, dict] = {}
        self.tabs_providers = QTabWidget()
        self.tabs_providers.addTab(self._openai_tab("local_llm", "http://localhost:11434/v1", "note_local_llm"), provider_label("local_llm"))
        self.tabs_providers.addTab(self._openai_tab("lmstudio", "http://localhost:1234/v1", "note_lmstudio"), provider_label("lmstudio"))
        self.tabs_providers.addTab(self._gemini_tab(), provider_label("gemini"))
        self.tabs_providers.addTab(self._google_tab(), provider_label("google"))
        lay.addWidget(self.tabs_providers)
        lay.addStretch(1)
        return _scroll(page)

    def _result_label(self, pid: str) -> QLabel:
        lab = QLabel("")
        lab.setWordWrap(True)
        self.pw[pid]["result"] = lab
        return lab

    def _buttons(self, pid: str, with_models: bool) -> tuple[QHBoxLayout, list[QPushButton]]:
        row = QHBoxLayout()
        btns: list[QPushButton] = []
        if with_models:
            b = QPushButton(t("btn_list_models"))
            b.clicked.connect(lambda: self._list_models(pid))
            row.addWidget(b)
            btns.append(b)
        t_btn = QPushButton(t("btn_test_conn"))
        t_btn.clicked.connect(lambda: self._test_provider(pid))
        row.addWidget(t_btn)
        btns.append(t_btn)
        row.addStretch(1)
        return row, btns

    def _key_row(self, pid: str, form: QFormLayout, label_key: str = "lbl_api_key") -> None:
        name = SECRET_FOR[pid]
        edit = secret_edit(t("key_placeholder_set"), self.ctx.secrets.has(name))
        delete = QPushButton(t("btn_delete_key"))
        delete.clicked.connect(lambda: self._mark_delete(pid, edit))
        box = QHBoxLayout()
        box.addWidget(edit, 1)
        box.addWidget(delete)
        lbl = QLabel(t(label_key))
        form.addRow(lbl, box)
        self.pw[pid]["key"] = edit
        self._key_rows.append((pid, lbl, edit, delete))

    def _mark_delete(self, pid: str, edit: QLineEdit) -> None:
        self._delete_secrets.add(SECRET_FOR[pid])
        edit.clear()
        edit.setPlaceholderText(t("key_placeholder_delete"))

    def _openai_tab(self, pid: str, url_hint: str, note_key: str) -> QWidget:
        self.pw[pid] = {}
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 12, 0, 0)
        card = Card()
        form = QFormLayout()
        form.setVerticalSpacing(12)
        url = QLineEdit()
        url.setPlaceholderText(url_hint)
        model = QComboBox()
        model.setEditable(True)
        model.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        lbl_url = QLabel(t("lbl_api_url"))
        lbl_model = QLabel(t("lbl_model_name"))
        form.addRow(lbl_url, url)
        form.addRow(lbl_model, model)
        self.pw[pid].update(url=url, model=model, lbl_url=lbl_url, lbl_model=lbl_model)
        self._key_row(pid, form, "lbl_api_key_opt")
        card.root.addLayout(form)
        note_lbl = muted_label(t(note_key))
        card.root.addWidget(note_lbl)
        btn_layout, btns = self._buttons(pid, True)
        card.root.addLayout(btn_layout)
        card.root.addWidget(self._result_label(pid))
        lay.addWidget(card)
        self._provider_tab_widgets.append((pid, note_lbl, btns))
        return w

    def _gemini_tab(self) -> QWidget:
        pid = "gemini"
        self.pw[pid] = {}
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 12, 0, 0)
        card = Card()
        form = QFormLayout()
        form.setVerticalSpacing(12)
        self._key_row(pid, form, "lbl_api_key")
        model = QComboBox()
        model.setEditable(True)
        model.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        model.addItems(GEMINI_SUGGESTIONS)
        url = QLineEdit()
        lbl_model = QLabel(t("lbl_model"))
        lbl_url = QLabel(t("lbl_api_url_adv"))
        form.addRow(lbl_model, model)
        form.addRow(lbl_url, url)
        self.pw[pid].update(model=model, url=url, lbl_model=lbl_model, lbl_url=lbl_url)
        card.root.addLayout(form)
        note_lbl = muted_label(t("note_gemini"))
        card.root.addWidget(note_lbl)
        btn_layout, btns = self._buttons(pid, True)
        card.root.addLayout(btn_layout)
        card.root.addWidget(self._result_label(pid))
        lay.addWidget(card)
        self._provider_tab_widgets.append((pid, note_lbl, btns))
        return w

    def _google_tab(self) -> QWidget:
        pid = "google"
        self.pw[pid] = {}
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 12, 0, 0)
        card = Card()
        form = QFormLayout()
        form.setVerticalSpacing(12)
        cloud = QCheckBox(t("chk_google_cloud"))
        card.root.addWidget(cloud)
        self.pw[pid]["cloud"] = cloud
        self._key_row(pid, form, "lbl_cloud_api_key")
        card.root.addLayout(form)
        note = muted_label(t("note_google"))
        note.setObjectName("Warn")
        card.root.addWidget(note)
        btn_layout, btns = self._buttons(pid, False)
        card.root.addLayout(btn_layout)
        card.root.addWidget(self._result_label(pid))
        lay.addWidget(card)
        self._provider_tab_widgets.append((pid, note, btns))
        return w

    def _build_hotkeys(self) -> QWidget:
        page, lay = self._page("page_hotkeys", "hotkeys_subtitle")
        card = Card()
        self.chk_hk_enabled = QCheckBox(t("chk_hk_enabled"))
        card.root.addWidget(self.chk_hk_enabled)
        form = QFormLayout()
        form.setVerticalSpacing(12)
        self.key_b = QKeySequenceEdit()
        self.key_n = QKeySequenceEdit()
        self.key_m = QKeySequenceEdit()
        self.key_v = QKeySequenceEdit()
        self.key_c = QKeySequenceEdit()
        self.key_o = QKeySequenceEdit()
        for e in (self.key_b, self.key_n, self.key_m, self.key_v, self.key_c, self.key_o):
            try:
                e.setMaximumSequenceLength(1)
            except AttributeError:
                pass
        self.lbl_hk_b = QLabel("")
        self.lbl_hk_n = QLabel("")
        self.lbl_hk_m = QLabel("")
        self.lbl_hk_v = QLabel("")
        self.lbl_hk_c = QLabel("")
        self.lbl_hk_o = QLabel("")
        for lab in (self.lbl_hk_b, self.lbl_hk_n, self.lbl_hk_m, self.lbl_hk_v, self.lbl_hk_c, self.lbl_hk_o):
            lab.setWordWrap(True)

        self.lbl_row_hk_b = QLabel(t("lbl_hk_b"))
        self.lbl_row_hk_n = QLabel(t("lbl_hk_n"))
        self.lbl_row_hk_m = QLabel(t("lbl_hk_m"))
        self.lbl_row_hk_v = QLabel(t("lbl_hk_v"))
        self.lbl_row_hk_c = QLabel(t("lbl_hk_c"))
        self.lbl_row_hk_o = QLabel(t("lbl_hk_o"))

        form.addRow(self.lbl_row_hk_b, self.key_b)
        form.addRow("", self.lbl_hk_b)
        form.addRow(self.lbl_row_hk_n, self.key_n)
        form.addRow("", self.lbl_hk_n)
        form.addRow(self.lbl_row_hk_o, self.key_o)
        form.addRow("", self.lbl_hk_o)
        form.addRow(self.lbl_row_hk_m, self.key_m)
        form.addRow("", self.lbl_hk_m)
        form.addRow(self.lbl_row_hk_v, self.key_v)
        form.addRow("", self.lbl_hk_v)
        form.addRow(self.lbl_row_hk_c, self.key_c)
        form.addRow("", self.lbl_hk_c)
        card.root.addLayout(form)

        self.btn_reset_hotkeys = QPushButton(t("btn_reset_hotkeys"))
        self.btn_reset_hotkeys.clicked.connect(self._reset_hotkeys)
        card.root.addWidget(self.btn_reset_hotkeys, 0, Qt.AlignmentFlag.AlignLeft)

        self.lbl_hk_note = muted_label(t("hotkeys_note"))
        card.root.addWidget(self.lbl_hk_note)
        lay.addWidget(card)
        lay.addStretch(1)
        return _scroll(page)

    def _build_privacy(self) -> QWidget:
        page, lay = self._page("page_privacy", "privacy_subtitle")
        card = Card()
        self.chk_history = QCheckBox(t("chk_history"))
        self.chk_cache = QCheckBox(t("chk_cache"))
        card.root.addWidget(self.chk_history)
        card.root.addWidget(self.chk_cache)
        self.btn_clear_history_p = QPushButton(t("btn_clear_history"))
        self.btn_clear_history_p.clicked.connect(self._clear_history)
        card.root.addWidget(self.btn_clear_history_p, 0, Qt.AlignmentFlag.AlignLeft)
        lay.addWidget(card)

        info = Card()
        self.lbl_privacy = QLabel("")
        self.lbl_privacy.setWordWrap(True)
        self.lbl_privacy.setTextFormat(Qt.TextFormat.RichText)
        info.root.addWidget(self.lbl_privacy)
        lay.addWidget(info)
        lay.addStretch(1)
        return _scroll(page)

    def _build_history(self) -> QWidget:
        page, lay = self._page("history_title")
        self.lbl_history_info = muted_label("")
        lay.addWidget(self.lbl_history_info)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([t("col_time"), t("col_provider"), t("col_target"), t("col_orig"), t("col_trans")])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table, 1)

        row = QHBoxLayout()
        self.btn_refresh_hist = QPushButton(t("btn_refresh"))
        self.btn_refresh_hist.clicked.connect(self._refresh_history)
        self.btn_copy_hist = QPushButton(t("btn_copy_selected"))
        self.btn_copy_hist.clicked.connect(self._copy_history)
        self.btn_clear_hist = QPushButton(t("btn_clear_history"))
        self.btn_clear_hist.clicked.connect(self._clear_history)

        row.addWidget(self.btn_refresh_hist)
        row.addWidget(self.btn_copy_hist)
        row.addWidget(self.btn_clear_hist)
        row.addStretch(1)
        lay.addLayout(row)
        return page

    # ================= dil değiştirme / retranslate =================
    def _on_ui_language_selected(self, index: int) -> None:
        lang_code = self.cmb_ui_lang.itemData(index)
        if lang_code and lang_code != get_ui_language():
            set_ui_language(lang_code)
            self.retranslate_ui()
            self.ui_language_changed.emit(lang_code)

    def retranslate_ui(self) -> None:
        """Etkin arayüz diline göre tüm etiketleri, butonları ve metinleri günceller."""
        self.setWindowTitle(t("window_title", app_name=APP_NAME))
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if is_rtl() else Qt.LayoutDirection.LeftToRight)

        # Sidebar tabs
        for i, key in enumerate(PAGE_KEYS):
            item = self.sidebar.item(i)
            if item:
                item.setText(t(key))

        self.save_btn.setText(t("btn_save"))

        # Sayfa başlıkları ve alt başlıkları
        for tl, sub, t_key, s_key in self._page_headers:
            tl.setText(t(t_key))
            if sub and s_key:
                sub.setText(t(s_key))

        # Genel sayfası
        self.lbl_ui_lang.setText(f"🌐  {t('lbl_ui_language')}")
        self.chk_autostart.setText(t("chk_autostart"))
        self.chk_tray.setText(t("chk_tray"))
        self.chk_notify.setText(t("chk_notify"))
        self.chk_autodetect.setText(t("chk_autodetect"))
        self.chk_keep.setText(t("chk_keep"))
        self.lbl_gen_footer.setText(t("general_footer", app_name=APP_NAME, version=__version__))

        # Diller sayfası
        self.lbl_row_pref.setText(t("lbl_pref_lang"))
        self.lbl_tip_pref.setText(t("lbl_pref_lang_tip"))
        self.lbl_row_b.setText(t("lbl_alt_b_lang"))
        self.lbl_tip_b.setText(t("lbl_alt_b_lang_tip"))
        self.lbl_row_n.setText(t("lbl_alt_n_lang"))
        self.lbl_tip_n.setText(t("lbl_alt_n_lang_tip"))
        self.lbl_row_src.setText(t("lbl_src_lang"))
        self.lbl_tip_src.setText(t("lbl_src_lang_tip"))
        self.cmb_pref.retranslate()
        self.cmb_b.retranslate()
        self.cmb_n.retranslate()
        self.cmb_src.retranslate()
        self.lbl_note_alt_m.setText(t("languages_note_alt_m"))
        self.lbl_prompt_title.setText(t("prompt_header"))
        self.lbl_presets.setText(t("lbl_presets"))
        self.btn_reset_prompt.setText(t("btn_reset_prompt"))
        self._populate_prompt_presets()
        self.txt_prompt.setPlaceholderText(t("prompt_placeholder"))
        self.lbl_prompt_help.setText(t("prompt_help"))

        # OCR sayfası
        self.lbl_ocr_engine.setText(t("ocr_engine_label"))
        cur_ocr_eng = self.cmb_ocr_engine.currentData()
        self.cmb_ocr_engine.blockSignals(True)
        self.cmb_ocr_engine.clear()
        self.cmb_ocr_engine.addItem(t("ocr_engine_auto"), "auto")
        self.cmb_ocr_engine.addItem(t("ocr_engine_windows"), "windows")
        self.cmb_ocr_engine.addItem(t("ocr_engine_gemini"), "gemini")
        if cur_ocr_eng:
            idx = self.cmb_ocr_engine.findData(cur_ocr_eng)
            self.cmb_ocr_engine.setCurrentIndex(max(0, idx))
        self.cmb_ocr_engine.blockSignals(False)

        self.lbl_ocr_target.setText(t("ocr_target_lang_label"))
        cur_ocr_target = self.cmb_ocr_target.code()
        self.cmb_ocr_target.retranslate()
        if cur_ocr_target:
            self.cmb_ocr_target.set_code(cur_ocr_target)
        else:
            self.cmb_ocr_target.setCurrentIndex(0)

        self.chk_ocr_fallback.setText(t("ocr_chk_fallback"))
        self.chk_ocr_clipboard.setText(t("ocr_chk_clipboard"))
        self.chk_ocr_notify.setText(t("ocr_chk_notify"))

        self.lbl_winocr_title.setText(t("ocr_installed_langs_title"))
        installed_langs = OcrService.get_installed_windows_ocr_languages()
        if installed_langs:
            self.lbl_winocr_status.setText(t("ocr_installed_langs_detected", langs=", ".join(installed_langs)))
        else:
            self.lbl_winocr_status.setText(t("ocr_no_installed_langs"))

        self.lbl_ocr_help_title.setText(t("ocr_how_to_use_title"))
        self.lbl_ocr_help_desc.setText(
            t("ocr_how_to_use_desc", hotkey=self.ctx.settings.settings.hotkeys.alt_o)
        )
        self.btn_ocr_hotkey.setText(t("ocr_btn_goto_hotkeys"))

        # Sağlayıcılar sayfası
        self.lbl_active_provider.setText(t("lbl_active_provider"))
        cur_act = self.cmb_active.currentData()
        self.cmb_active.blockSignals(True)
        self.cmb_active.clear()
        for pid in PROVIDER_IDS:
            self.cmb_active.addItem(provider_label(pid), pid)
        if cur_act:
            idx = self.cmb_active.findData(cur_act)
            self.cmb_active.setCurrentIndex(max(0, idx))
        self.cmb_active.blockSignals(False)
        self.chk_fallback.setText(t("chk_fallback"))
        self.warn_fallback.setText(t("providers_fallback_warn"))

        # Sağlayıcı sekmeleri
        self.tabs_providers.setTabText(0, provider_label("local_llm"))
        self.tabs_providers.setTabText(1, provider_label("lmstudio"))
        self.tabs_providers.setTabText(2, provider_label("gemini"))
        self.tabs_providers.setTabText(3, provider_label("google"))

        for pid, note_lbl, btns in self._provider_tab_widgets:
            if pid == "local_llm":
                note_lbl.setText(t("note_local_llm"))
                self.pw[pid]["lbl_url"].setText(t("lbl_api_url"))
                self.pw[pid]["lbl_model"].setText(t("lbl_model_name"))
                btns[0].setText(t("btn_list_models"))
                btns[1].setText(t("btn_test_conn"))
            elif pid == "lmstudio":
                note_lbl.setText(t("note_lmstudio"))
                self.pw[pid]["lbl_url"].setText(t("lbl_api_url"))
                self.pw[pid]["lbl_model"].setText(t("lbl_model_name"))
                btns[0].setText(t("btn_list_models"))
                btns[1].setText(t("btn_test_conn"))
            elif pid == "gemini":
                note_lbl.setText(t("note_gemini"))
                self.pw[pid]["lbl_model"].setText(t("lbl_model"))
                self.pw[pid]["lbl_url"].setText(t("lbl_api_url_adv"))
                btns[0].setText(t("btn_list_models"))
                btns[1].setText(t("btn_test_conn"))
            elif pid == "google":
                note_lbl.setText(t("note_google"))
                self.pw[pid]["cloud"].setText(t("chk_google_cloud"))
                btns[0].setText(t("btn_test_conn"))

        for pid, lbl, edit, delete in self._key_rows:
            delete.setText(t("btn_delete_key"))
            if pid == "google":
                lbl.setText(t("lbl_cloud_api_key"))
            elif pid in ("local_llm", "lmstudio"):
                lbl.setText(t("lbl_api_key_opt"))
            else:
                lbl.setText(t("lbl_api_key"))
            if not self.ctx.secrets.has(SECRET_FOR[pid]):
                edit.setPlaceholderText(t("key_placeholder_empty"))
            else:
                edit.setPlaceholderText(t("key_placeholder_set"))

        self._update_privacy_note()

        # Kısayollar sayfası
        self.chk_hk_enabled.setText(t("chk_hk_enabled"))
        self.lbl_row_hk_b.setText(t("lbl_hk_b"))
        self.lbl_row_hk_n.setText(t("lbl_hk_n"))
        self.lbl_row_hk_o.setText(t("lbl_hk_o"))
        self.lbl_row_hk_m.setText(t("lbl_hk_m"))
        self.lbl_row_hk_v.setText(t("lbl_hk_v"))
        self.lbl_row_hk_c.setText(t("lbl_hk_c"))
        self.btn_reset_hotkeys.setText(t("btn_reset_hotkeys"))
        self.lbl_hk_note.setText(t("hotkeys_note"))
        self._update_hotkey_status()

        # Gizlilik sayfası
        self.chk_history.setText(t("chk_history"))
        self.chk_cache.setText(t("chk_cache"))
        self.btn_clear_history_p.setText(t("btn_clear_history"))
        self._refresh_privacy_info()

        # Geçmiş sayfası
        self.table.setHorizontalHeaderLabels([t("col_time"), t("col_provider"), t("col_target"), t("col_orig"), t("col_trans")])
        self.btn_refresh_hist.setText(t("btn_refresh"))
        self.btn_copy_hist.setText(t("btn_copy_selected"))
        self.btn_clear_hist.setText(t("btn_clear_history"))
        self._refresh_history()

    # ================= yükleme / okuma =================
    def load_from_settings(self) -> None:
        s = self.ctx.settings.settings
        idx = self.cmb_ui_lang.findData(s.general.ui_language)
        self.cmb_ui_lang.blockSignals(True)
        self.cmb_ui_lang.setCurrentIndex(idx if idx >= 0 else 0)
        self.cmb_ui_lang.blockSignals(False)

        set_ui_language(s.general.ui_language)
        self.retranslate_ui()

        self.chk_autostart.setChecked(autostart.is_enabled() or s.general.start_with_windows)
        self.chk_tray.setChecked(s.general.minimize_to_tray)
        self.chk_notify.setChecked(s.general.notify_on_done)
        self.chk_autodetect.setChecked(s.general.auto_detect_source)
        self.chk_keep.setChecked(True)
        self.cmb_pref.set_code(s.languages.preferred_target)
        self.cmb_b.set_code(s.languages.alt_b_target)
        self.cmb_n.set_code(s.languages.alt_n_target)
        self.cmb_src.set_code(s.languages.source)
        prompt_val = s.languages.prompt if s.languages.prompt.strip() else DEFAULT_SYSTEM_PROMPT
        self.txt_prompt.setPlainText(prompt_val)
        matched_preset = 0
        for i, (_, tmpl) in enumerate(PROMPT_PRESETS, start=1):
            if prompt_val.strip() == tmpl.strip():
                matched_preset = i
                break
        self.cmb_prompt_presets.blockSignals(True)
        self.cmb_prompt_presets.setCurrentIndex(matched_preset)
        self.cmb_prompt_presets.blockSignals(False)

        # OCR ayarları
        ocr_cfg = getattr(s, "ocr", None)
        if ocr_cfg:
            idx = self.cmb_ocr_engine.findData(ocr_cfg.engine)
            self.cmb_ocr_engine.setCurrentIndex(max(0, idx))
            self.chk_ocr_fallback.setChecked(ocr_cfg.fallback_to_ai)
            self.chk_ocr_clipboard.setChecked(ocr_cfg.copy_to_clipboard)
            self.chk_ocr_notify.setChecked(ocr_cfg.show_notification)
            if ocr_cfg.target_language:
                self.cmb_ocr_target.set_code(ocr_cfg.target_language)
            else:
                self.cmb_ocr_target.setCurrentIndex(0)

        self.cmb_active.setCurrentIndex(max(0, self.cmb_active.findData(s.providers.active)))
        self.chk_fallback.setChecked(s.providers.auto_fallback)
        for pid in ("local_llm", "lmstudio", "gemini"):
            ep = getattr(s.providers, pid)
            self.pw[pid]["url"].setText(ep.base_url)
            self.pw[pid]["model"].setEditText(ep.model)
        self.pw["google"]["cloud"].setChecked(s.providers.google.use_cloud_api)
        self.chk_hk_enabled.setChecked(s.hotkeys.enabled)
        self.key_b.setKeySequence(QKeySequence(s.hotkeys.alt_b))
        self.key_n.setKeySequence(QKeySequence(s.hotkeys.alt_n))
        self.key_m.setKeySequence(QKeySequence(s.hotkeys.alt_m))
        self.key_v.setKeySequence(QKeySequence(s.hotkeys.alt_v))
        self.key_c.setKeySequence(QKeySequence(s.hotkeys.alt_c))
        self.key_o.setKeySequence(QKeySequence(s.hotkeys.alt_o))
        self.chk_history.setChecked(s.privacy.history_enabled)
        self.chk_cache.setChecked(s.privacy.cache_enabled)
        self._update_privacy_note()
        self._update_hotkey_status()

    @staticmethod
    def _seq_text(edit: QKeySequenceEdit, fallback: str) -> str:
        text = edit.keySequence().toString(QKeySequence.SequenceFormat.PortableText)
        return text or fallback

    def _read_form(self, s: Settings) -> None:
        s.general.ui_language = self.cmb_ui_lang.currentData() or "tr"
        s.general.start_with_windows = self.chk_autostart.isChecked()
        s.general.minimize_to_tray = self.chk_tray.isChecked()
        s.general.notify_on_done = self.chk_notify.isChecked()
        s.general.auto_detect_source = self.chk_autodetect.isChecked()
        s.general.keep_original_on_failure = True
        s.languages.preferred_target = self.cmb_pref.code() or "en"
        s.languages.alt_b_target = self.cmb_b.code()
        s.languages.alt_n_target = self.cmb_n.code()
        s.languages.source = self.cmb_src.code() or "auto"
        s.languages.prompt = self.txt_prompt.toPlainText().strip()
        if not hasattr(s, "ocr"):
            s.ocr = OcrSettings()
        s.ocr.engine = self.cmb_ocr_engine.currentData() or "auto"
        s.ocr.fallback_to_ai = self.chk_ocr_fallback.isChecked()
        s.ocr.copy_to_clipboard = self.chk_ocr_clipboard.isChecked()
        s.ocr.show_notification = self.chk_ocr_notify.isChecked()
        ocr_target = self.cmb_ocr_target.code()
        s.ocr.target_language = ocr_target if ocr_target else ""
        s.providers.active = self.cmb_active.currentData()
        s.providers.auto_fallback = self.chk_fallback.isChecked()
        for pid in ("local_llm", "lmstudio", "gemini"):
            ep = getattr(s.providers, pid)
            ep.base_url = self.pw[pid]["url"].text().strip()
            ep.model = self.pw[pid]["model"].currentText().strip()
        s.providers.google.use_cloud_api = self.pw["google"]["cloud"].isChecked()
        s.hotkeys.enabled = self.chk_hk_enabled.isChecked()
        s.hotkeys.alt_b = self._seq_text(self.key_b, s.hotkeys.alt_b)
        s.hotkeys.alt_n = self._seq_text(self.key_n, s.hotkeys.alt_n)
        s.hotkeys.alt_m = self._seq_text(self.key_m, s.hotkeys.alt_m)
        s.hotkeys.alt_v = self._seq_text(self.key_v, s.hotkeys.alt_v)
        s.hotkeys.alt_c = self._seq_text(self.key_c, s.hotkeys.alt_c)
        s.hotkeys.alt_o = self._seq_text(self.key_o, s.hotkeys.alt_o)
        s.privacy.history_enabled = self.chk_history.isChecked()
        s.privacy.cache_enabled = self.chk_cache.isChecked()

    # ================= kaydet =================
    def save(self) -> None:
        new = copy.deepcopy(self.ctx.settings.settings)
        self._read_form(new)
        problems = find_duplicates({
            "Alt+B kısayolu": new.hotkeys.alt_b,
            "Alt+N kısayolu": new.hotkeys.alt_n,
            "Alt+M kısayolu": new.hotkeys.alt_m,
            "Alt+V kısayolu": new.hotkeys.alt_v,
            "Alt+C kısayolu": new.hotkeys.alt_c,
            "Alt+O kısayolu": new.hotkeys.alt_o,
        })
        if problems:
            QMessageBox.warning(self, t("hk_err_title"), "\n".join(f"{k}: {v}" for k, v in problems.items()))
            self.sidebar.setCurrentRow(3)
            return
        self.ctx.settings.settings = new
        self.ctx.settings.save()
        set_ui_language(new.general.ui_language)
        self.ui_language_changed.emit(new.general.ui_language)

        for pid, edit in ((p, self.pw[p]["key"]) for p in SECRET_FOR):
            name = SECRET_FOR[pid]
            typed = edit.text().strip()
            try:
                if name in self._delete_secrets and not typed:
                    self.ctx.secrets.set(name, "")
                elif typed:
                    self.ctx.secrets.set(name, typed)
            except Exception:  # noqa: BLE001
                QMessageBox.warning(self, t("err_key_save_title"), t("err_key_save_msg"))
            edit.clear()
            edit.setPlaceholderText(t("key_placeholder_set") if self.ctx.secrets.has(name) else t("key_placeholder_empty"))
        self._delete_secrets.clear()
        try:
            autostart.set_enabled(new.general.start_with_windows)
        except OSError as exc:
            QMessageBox.warning(self, t("err_autostart_title"), t("err_autostart_msg", exc=exc))
        self.ctx.translation.clear_cache()
        self.ctx.hotkey_status.clear()
        self.ctx.hotkey_status.update(self.ctx.apply_hotkeys())
        self._update_hotkey_status()
        self._update_privacy_note()
        self._refresh_privacy_info()
        bad = [m for m in self.ctx.hotkey_status.values() if m]
        self.status.setObjectName("Err" if bad else "Ok")
        self.status.setStyleSheet("")
        self.status.setText(t("status_saved_warn") if bad else t("status_saved_ok"))
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def _update_hotkey_status(self) -> None:
        st = self.ctx.hotkey_status
        for key, lab in (
            ("alt_b", self.lbl_hk_b),
            ("alt_n", self.lbl_hk_n),
            ("alt_m", self.lbl_hk_m),
            ("alt_v", self.lbl_hk_v),
            ("alt_c", self.lbl_hk_c),
            ("alt_o", self.lbl_hk_o),
        ):
            msg = st.get(key)
            if not st:
                lab.setText("")
            elif msg:
                lab.setObjectName("Err")
                lab.setText("⚠ " + msg)
            else:
                lab.setObjectName("Ok")
                lab.setText(t("hk_registered"))
            lab.style().unpolish(lab)
            lab.style().polish(lab)

    def _reset_hotkeys(self) -> None:
        self.key_b.setKeySequence(QKeySequence("Alt+B"))
        self.key_n.setKeySequence(QKeySequence("Alt+N"))
        self.key_o.setKeySequence(QKeySequence("Alt+O"))
        self.key_m.setKeySequence(QKeySequence("Alt+M"))
        self.key_v.setKeySequence(QKeySequence("Alt+V"))
        self.key_c.setKeySequence(QKeySequence("Alt+C"))

    # ================= sağlayıcı test / model listesi =================
    def _temp_provider(self, pid: str):
        s = copy.deepcopy(self.ctx.settings.settings)
        self._read_form(s)
        mem = SecureStorage(MemoryBackend())
        for p, name in SECRET_FOR.items():
            typed = self.pw[p]["key"].text().strip()
            value = typed or ("" if name in self._delete_secrets else self.ctx.secrets.get(name))
            if value:
                mem.set(name, value)
        return PROVIDER_CLASSES[pid](lambda: s, mem)

    def _set_result(self, pid: str, text: str, ok: bool | None) -> None:
        lab: QLabel = self.pw[pid]["result"]
        lab.setObjectName({True: "Ok", False: "Err", None: "Subtle"}[ok])
        lab.setText(text)
        lab.style().unpolish(lab)
        lab.style().polish(lab)

    def _test_provider(self, pid: str) -> None:
        prov = self._temp_provider(pid)
        self._set_result(pid, t("status_testing"), None)

        def work() -> None:
            try:
                self.test_finished.emit(pid, True, prov.test_connection())
            except ProviderError as exc:
                self.test_finished.emit(pid, False, exc.message)
            except Exception as exc:  # noqa: BLE001
                self.test_finished.emit(pid, False, t("err_unexpected", err=type(exc).__name__))

        threading.Thread(target=work, daemon=True).start()

    def _on_test_finished(self, pid: str, ok: bool, msg: str) -> None:
        self._set_result(pid, ("✓ " if ok else "✗ ") + msg, ok)

    def _list_models(self, pid: str) -> None:
        prov = self._temp_provider(pid)
        self._set_result(pid, t("status_loading_models"), None)

        def work() -> None:
            try:
                self.models_loaded.emit(pid, prov.list_models(), "")
            except ProviderError as exc:
                self.models_loaded.emit(pid, [], exc.message)
            except Exception as exc:  # noqa: BLE001
                self.models_loaded.emit(pid, [], t("err_unexpected", err=type(exc).__name__))

        threading.Thread(target=work, daemon=True).start()

    def _on_models_loaded(self, pid: str, models: list, error: str) -> None:
        if error:
            self._set_result(pid, "✗ " + error, False)
            return
        combo: QComboBox = self.pw[pid]["model"]
        current = combo.currentText()
        combo.clear()
        combo.addItems(models)
        combo.setEditText(current if current in models or not models else (current or models[0]))
        self._set_result(pid, t("status_models_found", count=len(models)), True)

    # ================= gizlilik / geçmiş =================
    def _update_privacy_note(self) -> None:
        pid = self.cmb_active.currentData() or "google"
        offsite = pid in ("gemini", "google")
        prov_lbl = provider_label(pid)
        if offsite:
            self.lbl_privacy_note.setText(t("privacy_note_offsite", provider=prov_lbl))
        else:
            self.lbl_privacy_note.setText(t("privacy_note_local", provider=prov_lbl))

    def _refresh_privacy_info(self) -> None:
        s = self.ctx.settings.settings
        persistent = self.ctx.secrets.persistent
        history_state = t("state_open") if s.privacy.history_enabled else t("state_closed")
        sec_note = t("secret_persistent") if persistent else t("secret_memory")
        self.lbl_privacy.setText(
            t(
                "privacy_info_html",
                data_dir=data_dir(),
                history_state=history_state,
                history_path=history_path(),
                log_path=log_path(),
                secret_note=sec_note,
            )
        )

    def _refresh_history(self) -> None:
        s = self.ctx.settings.settings
        h_state = t("history_state_on") if s.privacy.history_enabled else t("history_state_off")
        self.lbl_history_info.setText(t("history_info", state=h_state, path=history_path()))
        entries = self.ctx.history.entries()
        self.table.setRowCount(len(entries))
        for r, e in enumerate(entries):
            raw_prov = e.get("provider", "")
            vals = [
                time.strftime("%d.%m.%Y %H:%M", time.localtime(e.get("t", 0))),
                provider_label(raw_prov) if raw_prov in PROVIDER_IDS else PROVIDER_LABELS.get(raw_prov, raw_prov),
                LanguageService.display_name(e.get("target", "")),
                e.get("src", ""),
                e.get("dst", ""),
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setToolTip(v)
                self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()

    def _copy_history(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if rows:
            QGuiApplication.clipboard().setText(self.table.item(rows[0].row(), 4).text())

    def _clear_history(self) -> None:
        if QMessageBox.question(self, t("confirm_clear_title"), t("confirm_clear_msg")) == QMessageBox.StandardButton.Yes:
            self.ctx.history.clear()
            self._refresh_history()

    def _on_page_changed(self, row: int) -> None:
        self.stack.setCurrentIndex(row)
        if row == 4:
            self._refresh_privacy_info()
        elif row == 5:
            self._refresh_history()

    def show_page(self, index: int) -> None:
        self.sidebar.setCurrentRow(index)
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.ctx.settings.settings.general.minimize_to_tray and not self.really_quit:
            event.ignore()
            self.hide()
        else:
            event.accept()
