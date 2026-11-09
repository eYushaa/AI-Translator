# 🌐 AITranslator v1.0.0 — No Barrier, No Border

### *Communicate effortlessly in any language across Windows with instant AI translation, OCR, and writing assistance.*

---

## 🚀 Welcome to AITranslator 1.0.0!

We are thrilled to announce the official first release of **AITranslator**! 

AITranslator is an intelligent, blazing-fast Windows desktop utility that brings cutting-edge AI translation, screen OCR capture, and writing enhancement directly into your daily workflow. It runs unobtrusively in your system tray and responds instantly across any application via simple global shortcuts.

---

## ✨ Features & Highlights

### ⌨️ Universal Global Shortcuts
- **`Alt + B` — In-Place Translation:** Select text anywhere (Slack, Outlook, Word, VS Code, Browser) and press `Alt + B`. The text is automatically translated and replaced directly where you typed it.
- **`Alt + N` — Floating Popup HUD:** Displays an instant translation in an elegant, shadow-cast floating tooltip next to your cursor without modifying your original text.
- **`Alt + O` — Screen Snip & OCR Translation:** Snip any region of your screen with an interactive crosshair; text is extracted and translated in real-time.
- **`Alt + M` — Quick Language Switcher:** Spotlight-style floating HUD to quickly search and switch your target language on-the-fly.
- **`Alt + V` — Fluency & Polish:** Rewrites selected text to sound natural, eloquent, and professional while preserving its original meaning and language.
- **`Alt + C` — Grammar & Spell Check:** Automatically fixes typos, punctuation, and grammatical mistakes in-place.

### 📸 Dual OCR Engine (Native Windows & AI Vision)
- **Fast & Offline:** Uses hardware-accelerated native `Windows.Media.Ocr` for instant offline text recognition.
- **AI Vision Fallback:** Automatically falls back to **Google Gemini Vision** when encountering complex images, stylized graphics, or multi-script captures.
- **Screen Snipper:** Fluid dimmed overlay with live dimension badge and Esc/right-click quick cancel.

### 🤖 Multi-Provider AI Architecture
- **Local & Offline LLMs:** Seamless integration with local OpenAI-compatible servers (Ollama, LM Studio, LocalAI, vLLM) for 100% offline and confidential workflows.
- **Cloud AI:** First-class support for Google Gemini (2.5 Flash, Pro, Lite) with ultra-low latency.
- **Google Translate Engine:** Built-in ready-to-use translation engine with no API key required, plus optional official Google Cloud Translation API support.
- **Automatic Fallback Chain:** If your primary AI model is unreachable or times out, requests automatically route to your configured fallback provider.

### 🎨 Translation Personas & Custom Prompts
Tailor translation style to your exact context:
- **Natural / Standard:** Fluent everyday tone.
- **Formal & Corporate:** Professional tone for business emails and documentation.
- **Casual & Friendly:** Natural conversational tone for chat apps and social messaging.
- **Academic & Technical:** High-precision translation for papers, technical terms, and code.
- **Concise Summary:** Distills long passages into quick bullet points.
- **Custom Prompt Editor:** Define custom system prompts with `{target}` and `{source}` variables.

### 🌍 10 Native UI Languages + RTL Support
Full interface localization accessible via the language picker in the settings window:
- 🇹🇷 Türkçe • 🇬🇧 English • 🇪🇸 Español • 🇫🇷 Français • 🇩🇪 Deutsch • 🇷🇺 Русский • 🇸🇦 العربية *(Full Right-to-Left RTL support)* • 🇨🇳 简体中文 • 🇯🇵 日本語 • 🇰🇷 한국어

### 🛡️ Privacy & Security by Design
- **Windows DPAPI Key Encryption:** API keys are never stored in plain text; they are encrypted using Windows Data Protection API (Credential Manager).
- **Lossless Clipboard Restoration:** Backs up and completely restores clipboard state (text, HTML, images, file references) after in-place replacement.
- **Active Window Focus Guard:** Automatically aborts paste operations if the target window focus shifts during translation.

---

## 📦 Downloads & Installation

| Asset | Description | Size |
| :--- | :--- | :--- |
| **`AITranslator-Setup.exe`** | Windows Inno Setup Installer *(Desktop icon, Start Menu, Auto-start option)* | Recommended |
| **`AITranslator.exe`** | Standalone Single-File Executable *(Portable, no installation required)* | ~51 MB |

### Checksums (SHA-256)
```text
AITranslator.exe: 7EDFB4CFF5A3E4F48216DBA8B004DB6336175E039B88BD52EDB33E90521FE5D3
```

---

## 💻 System Requirements
- **OS:** Windows 10 (Version 1903 or higher) / Windows 11 (64-bit)
- **Architecture:** x86_64 / amd64
- **Runtime:** Completely standalone (no Python installation or additional runtimes required)

---

**Full Changelog**: https://github.com/eYushaa/AI-Translator/commits/main
