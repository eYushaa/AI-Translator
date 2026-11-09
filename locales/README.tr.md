<div align="center">

# 🌐 AITranslator

### **No Barrier, No Border**

*Windows 10 ve 11 için modern, sistem geneli yapay zeka çeviri, OCR ve metin asistanı.*

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6?logo=windows&logoColor=white)](https://microsoft.com/windows)
[![Release](https://img.shields.io/badge/Release-v1.0.0-success?logo=github)](https://github.com/eYushaa/AI-Translator/releases)
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt-41CD52?logo=qt&logoColor=white)](https://www.qt.io/)
[![Lisans](https://img.shields.io/badge/Lisans-MIT-blue.svg)](../LICENSE)

---

**[English](../README.md) • [Türkçe](README.tr.md) • [Español](README.es.md) • [Français](README.fr.md) • [Deutsch](README.de.md) • [Русский](README.ru.md) • [العربية](README.ar.md) • [简体中文](README.zh.md) • [日本語](README.ja.md) • [한국어](README.ko.md)**

---

</div>

## 🌟 Genel Bakış

**AITranslator**, yüksek kaliteli yapay zeka çevirisini, ekrandan kırparak metin tanıma (OCR) özelliğini ve profesyonel metin parlatma yeteneklerini Windows sisteminizin her yerine getiren yeni nesil bir masaüstü uygulamasıdır.

Outlook'ta e-posta yazarken, Slack veya Discord'da mesajlaşırken, VS Code'da kod geliştirirken ya da internette gezinirken; kısayol tuşlarıyla işletim sisteminin herhangi bir yerinde doğrudan çalışır.

> **"No Barrier, No Border"** — Dil engellerini ve sınırları ortadan kaldırarak masaüstünüzde tam gizlilik ve sıfır sürtünmeyle özgürce iletişim kurun.

---

## 📥 İndirme ve Hızlı Başlangıç

Python, terminal veya karmaşık teknik ayarlarla uğraşmanıza gerek yoktur:

1. GitHub üzerindeki **[Releases (Sürümler)](https://github.com/eYushaa/AI-Translator/releases)** sayfasına gidin.
2. **`AITranslator-Setup.exe`** (Kurulum Sihirbazı) veya taşınabilir **`AITranslator.exe`** dosyasını indirin.
3. Dosyayı çalıştırıp kurulumu tamamlayın.
4. Uygulama **Windows Sistem Tepsisi**'nde (saatin yanında) sessizce başlar. Kısayollarınız kullanıma hazırdır!

---

## ✨ Özellikler

### 🚀 1. Sistem Geneli Kısayollar ve Yerinde Değiştirme
- **`Alt + B` — Yerinde Çeviri (In-Place):** Herhangi bir uygulamada bir metni seçin ve `Alt + B` tuşlarına basın. Seçili metin silinip yerine anında çevirisi yazılır.
- **`Alt + N` — Yüzen Açılır Pencere (Popup):** Orijinal metninizi değiştirmeden, çeviriyi imlecinizin hemen yanında beliren şık ve gölgeli açılır kutucukta gösterir.
- **`Alt + O` — Ekrandan Kırpma & OCR Çevirisi:** Ekranınızdaki herhangi bir yazı alanını fareyle seçin; sistem metni anında tanır ve seçimin yanında çevirisini gösterir.
- **`Alt + M` — Hızlı Hedef Dil Değiştirici (HUD):** Hedef çeviri dilini anında değiştirmek için Spotlight tarzı hızlı seçim menüsünü açar.
- **`Alt + V` — Metin İyileştirme & Akıcılık:** Seçtiğiniz metni dilini değiştirmeden daha profesyonel, akıcı ve etkileyici bir üslupla yeniden yazar.
- **`Alt + C` — İmla ve Dilbilgisi Düzeltme:** Seçili metindeki tüm yazım yanlışlarını, noktalama hatalarını ve dilbilgisi bozukluklarını tek hamlede düzeltir.

---

### 📸 2. Gelişmiş Ekran OCR (Windows Yerel & Gemini Vision)
- **Ultra Hızlı & Çevrimdışı:** İnternet gerektirmeden, doğrudan Windows'un dahili `Windows.Media.Ocr` motorunu kullanarak donanım hızlandırmalı metin tanıma sağlar.
- **Yapay Zeka Vision Desteği:** Yerel OCR metin tespit edemediğinde veya stilize fontlarla karşılaşıldığında otomatik olarak **Google Gemini Vision** modeline geçer.
- **Etkileşimli Ekran Kırpıcı:** Karartılmış katman, artı imleç, piksel boyut rozeti; sağ tık veya Esc ile anında iptal.
- **Panoya Otomatik Kopyalama:** Tanınan orijinal metni otomatik olarak panonuza kopyalama seçeneği.

---

### 🤖 3. Çoklu Sağlayıcı Mimarisi ve Otomatik Yedekleme
İster yerel ister bulut tabanlı yapay zeka modellerinizi bağlayın:
- **Yerel LLM'ler (Ollama / LocalAI / vLLM):** OpenAI uyumlu yerel sunucular (`http://localhost:11434/v1`) üzerinden %100 çevrimdışı ve gizli çeviri.
- **LM Studio:** Model listeleme ve bağlantı testi desteğiyle doğrudan entegrasyon (`http://localhost:1234/v1`).
- **Google Gemini:** Kendi API anahtarınızla Gemini 2.5 Flash, Pro ve Lite modelleriyle ultra hızlı çeviri.
- **Google Translate:** API anahtarı gerektirmeyen hazır çeviri motoru ve resmî Cloud Translation API desteği.
- **Otomatik Yedekleme Zinciri (Fallback):** Bir sağlayıcı çevrimdışı olduğunda istek otomatik olarak belirlediğiniz diğer sağlayıcıya yönlendirilir.

---

### 🎨 4. Çeviri Üslupları ve Özel Prompt Desteği
Çevirilerinizi ihtiyacınıza göre uyarlayın:
- **Doğal / Standart:** Günlük konuşma akışına uygun, doğal ve akıcı ifadeler.
- **Resmi ve Kurumsal:** İş e-postaları ve resmî yazışmalar için kurumsal ve profesyonel ton.
- **Günlük ve Samimi:** Sosyal medya ve sohbet uygulamaları için samimi ve doğal üslup.
- **Akademik ve Teknik:** Bilimsel makaleler, terimler ve kodlar için yüksek hassasiyet.
- **Kısa ve Öz Özetleme:** Uzun yabancı metinleri ana hatlarıyla özetler.
- **Özel Sistem Promptu:** `{target}` ve `{source}` parametreleriyle kendi kurallarınızı belirleyin.

---

### 🌍 5. 10 Farklı Arayüz Dili ve Sağdan Sola (RTL) Desteği
Ayarlar penceresinin sol altındaki dil seçiciden uygulamanın tüm arayüzünü anında değiştirebilirsiniz:
- 🇹🇷 Türkçe • 🇬🇧 English • 🇫🇷 Français • 🇩🇪 Deutsch • 🇪🇸 Español • 🇷🇺 Русский • 🇸🇦 العربية *(Tam RTL)* • 🇨🇳 简体中文 • 🇯🇵 日本語 • 🇰🇷 한국어

---

### 🛡️ 6. Tasarımdan Gelen Güvenlik ve Gizlilik
- **Kusursuz Pano Koruma:** Çeviri sırasında pano yedeklenir ve işlem bittiğinde tüm biçimleriyle (metin, HTML, görsel, dosya listeleri) orijinal haline geri yüklenir.
- **Şifreli Anahtar Depolama:** API anahtarları düz metin JSON dosyalarında **saklanmaz**. Windows DPAPI (Kimlik Bilgisi Yöneticisi) ile şifrelenir.
- **Pencere ve Odak Koruması:** Çeviri sürerken başka bir pencereye geçilirse işlem iptal edilir; yanlış yere metin yapıştırılması engellenir.

---

## 📸 Ekran Görüntüleri

| Diller ve Özel Promptlar | OCR & Ekran Alıntısı Ayarları |
|:---:|:---:|
| ![Diller](../docs/screenshots/1_languages.png) | ![OCR Ayarları](../docs/screenshots/2_ocr.png) |

| Yapay Zeka Sağlayıcıları | Sistem Geneli Kısayollar |
|:---:|:---:|
| ![Sağlayıcılar](../docs/screenshots/3_providers.png) | ![Kısayollar](../docs/screenshots/4_shortcuts.png) |

| Hızlı Dil Seçici (Alt+M) | Yüzen Çeviri Kutucuğu (Alt+N) |
|:---:|:---:|
| ![Hızlı Dil Seçici](../docs/screenshots/7_language_picker.png) | ![Çeviri Kutusu](../docs/screenshots/8_translation_popup.png) |

| Genel Ayarlar & Arayüz Dili Barı | Gizlilik ve Önbellek Kontrolü |
|:---:|:---:|
| ![Genel](../docs/screenshots/0_general.png) | ![Gizlilik](../docs/screenshots/5_privacy.png) |

---

## ⌨️ Varsayılan Kısayol Tuşları

| Kısayol | İşlem | Açıklama |
|:---|:---|:---|
| <kbd>Alt</kbd> + <kbd>B</kbd> | **Yerinde Değiştirerek Çevir** | Seçili metni doğrudan çevirisiyle değiştirir. |
| <kbd>Alt</kbd> + <kbd>N</kbd> | **Açılır Kutuda Çevir** | Metni değiştirmeden yüzen popup kutucuğunda gösterir. |
| <kbd>Alt</kbd> + <kbd>O</kbd> | **Ekrandan Kırp & Çevir (OCR)** | Ekrandaki herhangi bir yazı alanını seçerek anında çevirir. |
| <kbd>Alt</kbd> + <kbd>M</kbd> | **Hızlı Hedef Dil Değiştirici** | Hedef dili hızlıca değiştirmek için arama menüsünü açar. |
| <kbd>Alt</kbd> + <kbd>V</kbd> | **Metin İyileştirme (Akıcılık)** | Metni aynı dilde daha etkili ve profesyonel hale getirir. |
| <kbd>Alt</kbd> + <kbd>C</kbd> | **İmla ve Dilbilgisi Düzeltme** | Metindeki yazım ve gramer hatalarını düzeltir. |

---

## 📄 Lisans

Bu proje [MIT Lisansı](../LICENSE) kapsamında lisanslanmıştır.
