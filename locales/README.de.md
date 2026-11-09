<div align="center">

# 🌐 AITranslator

### **No Barrier, No Border**

*Ein moderner, systemweiter KI-Übersetzungs-, OCR- und Schreibassistent für Windows 10 & 11.*

[![Plattform](https://img.shields.io/badge/Plattform-Windows%2010%20%2F%2011-0078D6?logo=windows&logoColor=white)](https://microsoft.com/windows)
[![Release](https://img.shields.io/badge/Release-v1.0.0-success?logo=github)](https://github.com/eYushaa/AI-Translator/releases)
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt-41CD52?logo=qt&logoColor=white)](https://www.qt.io/)
[![Lizenz](https://img.shields.io/badge/Lizenz-MIT-blue.svg)](../LICENSE)

---

**[English](../README.md) • [Türkçe](README.tr.md) • [Español](README.es.md) • [Français](README.fr.md) • [Deutsch](README.de.md) • [Русский](README.ru.md) • [العربية](README.ar.md) • [简体中文](README.zh.md) • [日本語](README.ja.md) • [한국어](README.ko.md)**

---

</div>

## 🌟 Überblick

**AITranslator** ist ein intelligentes, blitzschnelles Windows-Dienstprogramm, das erstklassige KI-Übersetzung, Texterkennung vom Bildschirm (OCR) und Textoptimierung direkt auf Tastendruck bereitstellt.

Ganz gleich, ob Sie E-Mails in Outlook verfassen, in Slack/Discord chatten, in VS Code programmieren oder im Internet surfen: AITranslator funktioniert überall über intuitive Tastenkombinationen.

> **„No Barrier, No Border“** — Grenzenlos und barrierefrei in jeder Sprache kommunizieren, mit maximalem Datenschutz.

---

## 📥 Download & Schnelleinrichtung

Keine technischen Kenntnisse oder Python-Installationen erforderlich:

1. Besuchen Sie den Bereich **[Releases](https://github.com/eYushaa/AI-Translator/releases)** auf GitHub.
2. Laden Sie den Installer **`AITranslator-Setup.exe`** oder die portable Version **`AITranslator.exe`** herunter.
3. Starten Sie das Setup und öffnen Sie die Anwendung.
4. Das Programm startet leise im **Windows-Systemabschnitt (System Tray)** neben der Uhrzeit.

---

## ✨ Wichtigste Funktionen

### 🚀 1. Globale Tastenkombinationen & Direkt-Ersetzung
- **`Alt + B` — Direkt-Übersetzung (In-Place):** Beliebigen Text markieren und `Alt + B` drücken. Der Text wird sofort an Ort und Stelle durch die Übersetzung ersetzt.
- **`Alt + N` — Schwebendes Popup-Fenster:** Zeigt die Übersetzung in einem eleganten Infofenster neben dem Mauszeiger an, ohne das Original zu verändern.
- **`Alt + O` — Bildschirmschnitt & OCR:** Beliebigen Bildschirmbereich markieren; erkannter Text wird sofort ausgelesen und übersetzt.
- **`Alt + M` — Schnelle Zielsprachauswahl:** Ändern Sie Ihre Zielsprache jederzeit blitzschnell über ein zentriertes Suchfenster.
- **`Alt + V` — Text polieren & optimieren:** Formuliert den markierten Text um, damit er flüssiger, professioneller und stilistisch eleganter klingt.
- **`Alt + C` — Grammatik- & Rechtschreibkorrektur:** Korrigiert Tippfehler und Grammatikfehler direkt an Ort und Stelle.

---

### 📸 2. Duale OCR-Engine (Natives Windows & KI-Vision)
- **Schnell & Offline:** Nutzt hardwarebeschleunigtes natives `Windows.Media.Ocr` für sofortige Offline-Texterkennung ohne Internetverbindung.
- **KI-Vision-Fallback:** Erkennt das lokale OCR keinen Text, wechselt das System automatisch zu **Google Gemini Vision**.
- **Fadenkreuz-Auswahl:** Abgedunkelter Bildschirm mit Pixelgrößenanzeige; Abbruch jederzeit mit Escape oder Rechtsklick.

---

### 🤖 3. Multi-Provider-KI & Lokale LLMs
- **Lokale LLMs (Ollama / LocalAI / vLLM):** 100 % privat und offline über OpenAI-kompatible Schnittstellen (`http://localhost:11434/v1`).
- **LM Studio:** Direkte Integration lokaler Modelle (`http://localhost:1234/v1`).
- **Google Gemini:** Höchste Geschwindigkeit und Präzision mit Gemini 2.5 Flash, Pro oder Lite.
- **Google Translate:** Sofort einsatzbereit ohne API-Schlüssel, optional mit offizieller Google Cloud Translation API.
- **Automatischer Fallback:** Bei Ausfall eines Anbieters springt automatisch die nächste konfigurierte KI ein.

---

## 📸 Screenshots

| Sprachen & Eigene Prompts | OCR & Bildschirmschnitt-Optionen |
|:---:|:---:|
| ![Sprachen](../docs/screenshots/1_languages.png) | ![OCR-Einstellungen](../docs/screenshots/2_ocr.png) |

| KI-Anbieter & Endpunkte | Globale Tastenkombinationen |
|:---:|:---:|
| ![Anbieter](../docs/screenshots/3_providers.png) | ![Kombinationen](../docs/screenshots/4_shortcuts.png) |

| Schnellauswahl der Zielsprache (Alt+M) | Schwebendes Infofenster (Alt+N) |
|:---:|:---:|
| ![Schnellauswahl](../docs/screenshots/7_language_picker.png) | ![Infofenster](../docs/screenshots/8_translation_popup.png) |

| Allgemeine Einstellungen & Sprachleiste | Datenschutz & Verlauf |
|:---:|:---:|
| ![Allgemein](../docs/screenshots/0_general.png) | ![Datenschutz](../docs/screenshots/5_privacy.png) |

---

## ⌨️ Tastaturkürzel

| Tastenkombination | Aktion | Beschreibung |
|:---|:---|:---|
| <kbd>Alt</kbd> + <kbd>B</kbd> | **Direkt übersetzen** | Ersetzt den markierten Text direkt durch die Übersetzung. |
| <kbd>Alt</kbd> + <kbd>N</kbd> | **Im Popup anzeigen** | Öffnet die Übersetzung in einem schwebenden Fenster. |
| <kbd>Alt</kbd> + <kbd>O</kbd> | **OCR-Bildschirmschnitt** | Bildschirmbereich auswählen, Text erkennen und übersetzen. |
| <kbd>Alt</kbd> + <kbd>M</kbd> | **Zielsprache wechseln** | Öffnet die Schnellauswahl für die Übersetzungssprache. |
| <kbd>Alt</kbd> + <kbd>V</kbd> | **Text polieren** | Verbessert Stil und Formulierung in derselben Sprache. |
| <kbd>Alt</kbd> + <kbd>C</kbd> | **Grammatik korrigieren** | Behebt Tipp- und Grammatikfehler automatisch. |

---

## 📄 Lizenz

Dieses Projekt ist unter der [MIT-Lizenz](../LICENSE) lizenziert.
