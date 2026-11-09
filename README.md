<div align="center">

# 🌐 AITranslator

### **No Barrier, No Border**

*A modern, system-wide AI translation, OCR, and writing assistant for Windows 10 & 11.*

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6?logo=windows&logoColor=white)](https://microsoft.com/windows)
[![Release](https://img.shields.io/badge/Release-v1.0.0-success?logo=github)](https://github.com/eYushaa/AI-Translator/releases)
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt-41CD52?logo=qt&logoColor=white)](https://www.qt.io/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

**[English](README.md) • [Türkçe](locales/README.tr.md) • [Español](locales/README.es.md) • [Français](locales/README.fr.md) • [Deutsch](locales/README.de.md) • [Русский](locales/README.ru.md) • [العربية](locales/README.ar.md) • [简体中文](locales/README.zh.md) • [日本語](locales/README.ja.md) • [한국어](locales/README.ko.md)**

---

</div>

## 🌟 Overview

**AITranslator** is an intelligent, blazing-fast Windows desktop utility that brings high-quality AI translation, screen OCR capture, and writing enhancement across your entire operating system.

Whether composing emails in Outlook, chatting in Slack/Discord, coding in VS Code, reading PDFs, or browsing the web, AITranslator seamlessly integrates with your workflow through simple global shortcuts.

> **"No Barrier, No Border"** — Communicate effortlessly in any language, anywhere on your desktop, with zero friction and total privacy.

---

## 📥 Download & Quick Start

You don't need Python, terminals, or complex configurations:

1. Go to the **[Releases](https://github.com/eYushaa/AI-Translator/releases)** section on GitHub.
2. Download **`AITranslator-Setup.exe`** (Installer) or standalone **`AITranslator.exe`**.
3. Run the setup and open the app.
4. The application starts quietly in your **Windows System Tray** (near the clock). You are ready to translate instantly!

---

## ✨ Features

### 🚀 1. Universal Hotkeys & In-Place Replacement
- **`Alt + B` — In-Place Translation:** Select any text and press `Alt + B`. The selected text is instantly replaced by its translation directly where you typed it.
- **`Alt + N` — Floating Popup Tooltip:** Translates selected text in an elegant, shadow-cast floating HUD next to your cursor without altering your original text.
- **`Alt + O` — Screen Snip & OCR Translation:** Snip any region of your screen; detected text is recognized and translated instantly.
- **`Alt + M` — Quick Language Switcher:** Change your target translation language on-the-fly via a Spotlight-style HUD with instant search.
- **`Alt + V` — Polish & Enhance Fluency:** Rephrases selected text to sound natural, eloquent, and professional without altering language or core intent.
- **`Alt + C` — Spelling & Grammar Fix:** Automatically corrects typos, punctuation, and grammatical mistakes in-place.

---

### 📸 2. Dual OCR Engine (Native Windows & AI Vision)
- **Fast & Offline:** Uses hardware-accelerated native `Windows.Media.Ocr` for instant offline text recognition.
- **AI Vision Fallback:** If native OCR cannot detect text or encounters complex fonts/images, it automatically falls back to **Google Gemini Vision**.
- **Crosshair Screen Snipper:** Dimmed overlay with pixel dimension badge and right-click/Esc quick cancel.
- **Clipboard Integration:** Option to automatically copy recognized text straight to your clipboard.

---

### 🤖 3. Multi-Provider AI & Local LLM Support
Choose and switch between your favorite local and cloud providers:
- **Local LLMs (Ollama / LocalAI / vLLM):** 100% private, offline inference via OpenAI-compatible API (`http://localhost:11434/v1`).
- **LM Studio:** Direct local model integration (`http://localhost:1234/v1`).
- **Google Gemini:** High-speed cloud translations using Gemini 2.5 Flash, Pro, or Lite with your own API key.
- **Google Translate:** Zero-config translation with no API key required, plus optional official Google Cloud Translation API support.
- **Automatic Fallback Chain:** If your active provider goes offline or exceeds quota, requests seamlessly fall back to your secondary providers.

---

### 🎨 4. Writing Styles & Custom Prompts
Choose between tailored preset modes or create your own:
- **Natural / Standard:** Fluent everyday phrasing.
- **Formal & Corporate:** Professional tone for business emails and official correspondence.
- **Casual & Friendly:** Conversational flow for social media and chat.
- **Academic & Technical:** High rigor and terminology preservation for scientific papers.
- **Concise Summary:** Condenses foreign text into essential key points.
- **Custom System Prompt:** Fully customize prompts using `{target}` and `{source}` placeholders.

---

### 🌍 5. 10 UI Languages & Native RTL Layout
Change the app's interface language anytime from the persistent bottom-left bar:
- 🇹🇷 Türkçe • 🇬🇧 English • 🇫🇷 Français • 🇩🇪 Deutsch • 🇪🇸 Español • 🇷🇺 Русский • 🇸🇦 العربية *(Full RTL)* • 🇨🇳 简体中文 • 🇯🇵 日本語 • 🇰🇷 한국어

---

### 🛡️ 6. Privacy & Safety by Design
- **Complete Clipboard Protection:** Backs up and restores all clipboard formats (text, HTML, images, file lists) with zero pollution.
- **DPAPI Key Encryption:** API keys are encrypted via **Windows Credential Locker (DPAPI)** and never saved in plaintext files.
- **Focus Guard:** Translations abort safely if the active window changes during processing, preventing unintended paste actions.

---

## 📸 Screenshots

| Languages & Dedicated Prompts | OCR & Screen Snip Settings |
|:---:|:---:|
| ![Languages](docs/screenshots/1_languages.png) | ![OCR Settings](docs/screenshots/2_ocr.png) |

| AI Providers & Endpoints | System-Wide Shortcuts |
|:---:|:---:|
| ![Providers](docs/screenshots/3_providers.png) | ![Shortcuts](docs/screenshots/4_shortcuts.png) |

| Quick Language Switcher (Alt+M) | Floating Translation Popup (Alt+N) |
|:---:|:---:|
| ![Language Switcher](docs/screenshots/7_language_picker.png) | ![Popup](docs/screenshots/8_translation_popup.png) |

| General Settings & Multi-Language Bar | Privacy & History Control |
|:---:|:---:|
| ![General](docs/screenshots/0_general.png) | ![Privacy](docs/screenshots/5_privacy.png) |

---

## ⌨️ Shortcut Reference

| Shortcut | Feature | Description |
|:---|:---|:---|
| <kbd>Alt</kbd> + <kbd>B</kbd> | **In-Place Translation** | Replaces highlighted text directly with translation. |
| <kbd>Alt</kbd> + <kbd>N</kbd> | **Popup Translation** | Shows translation in a modern floating window. |
| <kbd>Alt</kbd> + <kbd>O</kbd> | **Screen Snip & OCR** | Select any screen area to scan and translate text. |
| <kbd>Alt</kbd> + <kbd>M</kbd> | **Language Switcher** | Opens quick target language selector HUD. |
| <kbd>Alt</kbd> + <kbd>V</kbd> | **Polish & Fluency** | Rephrases text for clarity, style, and fluency. |
| <kbd>Alt</kbd> + <kbd>C</kbd> | **Spelling & Grammar** | Automatically fixes grammar and spelling errors. |

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
