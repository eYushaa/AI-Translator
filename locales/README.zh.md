<div align="center">

# 🌐 AITranslator

### **No Barrier, No Border**

*专为 Windows 10 与 11 打造的现代全局 AI 翻译、屏幕 OCR 与写作润色助手。*

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6?logo=windows&logoColor=white)](https://microsoft.com/windows)
[![Release](https://img.shields.io/badge/Release-v1.0.0-success?logo=github)](https://github.com/eYushaa/AI-Translator/releases)
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt-41CD52?logo=qt&logoColor=white)](https://www.qt.io/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](../LICENSE)

---

**[English](../README.md) • [Türkçe](README.tr.md) • [Español](README.es.md) • [Français](README.fr.md) • [Deutsch](README.de.md) • [Русский](README.ru.md) • [العربية](README.ar.md) • [简体中文](README.zh.md) • [日本語](README.ja.md) • [한국어](README.ko.md)**

---

</div>

## 🌟 简介

**AITranslator** 是一款功能强大、响应极速的 Windows 系统级翻译工具，可在操作系统任意角落为您提供高质量的 AI 翻译、屏幕截屏文字识别（OCR）以及地道的文本润色与纠错。

无论您是在 Outlook 中撰写邮件、在 Slack/Discord 聊天、在 VS Code 中编写代码，还是在浏览器中阅读文献，AITranslator 都能通过简单顺手的全局快捷键无缝融入您的工作流。

> **“No Barrier, No Border”** —— 跨越语言障碍，畅通无阻，保障极致隐私。

---

## 📥 下载与快速开始

无需安装 Python、打开终端或进行复杂的命令行配置：

1. 前往 GitHub 仓库的 **[Releases (发布页面)](https://github.com/eYushaa/AI-Translator/releases)**。
2. 下载 **`AITranslator-Setup.exe`**（安装包）或单文件免安装版 **`AITranslator.exe`**。
3. 运行并完成安装，启动应用程序。
4. 软件将静默驻留在右下角的 **Windows 系统托盘**（时钟旁），随时待命！

---

## ✨ 核心特性

### 🚀 1. 全局快捷键与原地替换翻译
- **`Alt + B` — 原地翻译：** 选中文本后按下 `Alt + B`，所选文字会直接被目标语言的翻译替换。
- **`Alt + N` — 悬浮弹窗翻译：** 在光标附近优雅地弹出带阴影的气泡窗口显示翻译，不更改您的原文。
- **`Alt + O` — 屏幕截图与 OCR 翻译：** 框选屏幕任意区域（图片、视频、PDF、网页等），自动识别并翻译文字。
- **`Alt + M` — 快捷切换目标语言：** 唤出 Spotlight 风格的居中搜索栏，随心切换目标翻译语言。
- **`Alt + V` — AI 文本润色与表达增强：** 在不改变原始语言和含义的前提下，将句子重构得更加地道、流畅和专业。
- **`Alt + C` — 拼写与语法自动纠错：** 一键修正错别字、标点符号及语法瑕疵。

---

### 📸 2. 双引擎 OCR 识别（Windows 本地与 AI 视觉模型）
- **极速与离线可用：** 优先调用原生硬件加速的 `Windows.Media.Ocr`，无需网络也能瞬间识别屏幕文字。
- **AI Vision 深度备用：** 若本地 OCR 遇到艺术字体或未检出文本，将自动调用 **Google Gemini Vision** 进行识别。
- **顺畅的截屏交互：** 屏幕变暗、十字光标与像素尺寸标注，支持鼠标右键或 Esc 键快速取消。

---

### 🤖 3. 多模型与本地大语言模型（LLM）支持
- **本地大模型（Ollama / LocalAI / vLLM）：** 通过 OpenAI 兼容 API (`http://localhost:11434/v1`) 实现 100% 离线、纯私密推理。
- **LM Studio：** 一键直连本地部署的模型服务 (`http://localhost:1234/v1`)。
- **Google Gemini：** 支持 Gemini 2.5 Flash / Pro 高速云端翻译（使用个人 API 密钥）。
- **Google Translate：** 开箱即用，无需配置任何 API 密钥。

---

## 📸 界面截图

| 语言与自定义提示词 | 屏幕截图与 OCR 设置 |
|:---:|:---:|
| ![语言设置](../docs/screenshots/1_languages.png) | ![OCR 设置](../docs/screenshots/2_ocr.png) |

| AI 模型提供方与终端 | 全局快捷键设置 |
|:---:|:---:|
| ![AI 提供方](../docs/screenshots/3_providers.png) | ![快捷键](../docs/screenshots/4_shortcuts.png) |

| 快捷语言切换菜单 (Alt+M) | 悬浮翻译提示框 (Alt+N) |
|:---:|:---:|
| ![语言切换](../docs/screenshots/7_language_picker.png) | ![翻译弹窗](../docs/screenshots/8_translation_popup.png) |

| 常规设置与语言切换栏 | 隐私与历史记录控制 |
|:---:|:---:|
| ![常规设置](../docs/screenshots/0_general.png) | ![隐私控制](../docs/screenshots/5_privacy.png) |

---

## ⌨️ 快捷键速查

| 快捷键 | 功能 | 说明 |
|:---|:---|:---|
| <kbd>Alt</kbd> + <kbd>B</kbd> | **原地翻译** | 直接将划词选中的文本替换为翻译结果。 |
| <kbd>Alt</kbd> + <kbd>N</kbd> | **弹窗翻译** | 在优雅的悬浮提示框中查看翻译，不修改原文。 |
| <kbd>Alt</kbd> + <kbd>O</kbd> | **屏幕 OCR 翻译** | 截取屏幕任意区域并提取、翻译其中文字。 |
| <kbd>Alt</kbd> + <kbd>M</kbd> | **快速切换语言** | 打开目标翻译语言快捷切换搜索窗。 |
| <kbd>Alt</kbd> + <kbd>V</kbd> | **润色与修饰** | 优化选中文本的文风与表达，使其更自然流畅。 |
| <kbd>Alt</kbd> + <kbd>C</kbd> | **纠正语法拼写** | 自动修复所选文字中的错别字与语法错误。 |

---

## 📄 开源许可证

本项目基于 [MIT 许可证](../LICENSE) 开源。
