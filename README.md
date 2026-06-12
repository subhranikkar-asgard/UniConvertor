# UniConvertor 🚀

A **free, universal file converter and compressor** — convert and compress images, PDFs, and Word documents right from your browser or Android phone.

![UniConvertor](static/assets/hero_bg.png)

---

## ✨ Features

- 🖼️ **Image conversion** — PNG ↔ JPG ↔ WebP ↔ BMP ↔ GIF ↔ TIFF ↔ ICO ↔ PDF
- 📄 **PDF tools** — Compress · Convert to Word · Convert to Images (ZIP)
- 📝 **Word tools** — Convert to PDF · Convert to Images (ZIP)
- 🗜️ **3 compression levels** — Maximum · Recommended · Minimum
- 📱 **Android APK** — WebView companion app for mobile use
- 🔒 **Privacy first** — files auto-deleted after 2 minutes
- 💸 **100% Free** — no sign-up, no watermarks, no limits

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python · Flask |
| Frontend | HTML · Tailwind CSS · Vanilla JS |
| Image processing | Pillow |
| PDF processing | PyMuPDF (fitz) |
| PDF → Word | pdf2docx |
| Word → PDF | docx2pdf |
| Android | Kotlin · Jetpack Compose · WebView |

---

## 🚀 Running Locally

### Prerequisites
```bash
pip install flask pillow pymupdf pdf2docx docx2pdf werkzeug
```

### Start the server
```bash
python app.py
```

Open **http://localhost:5000** in your browser.

To access from your **phone** on the same Wi-Fi, use your PC's local IP:
```
http://192.168.x.x:5000
```

---

## 📱 Android APK

The `android/` folder contains a Kotlin + Jetpack Compose app that wraps the web UI in a full-screen WebView.

### Build the APK
```bash
cd android
# Windows (requires JDK 17+)
set JAVA_HOME=C:\Program Files\Android\Android Studio\jbr
gradlew.bat assembleDebug
```

APK output: `android/app/build/outputs/apk/debug/app-debug.apk`

### How to use
1. Install the APK on your Android phone
2. Enter your PC's local IP address and port (`5000`)
3. Tap **Connect** — the full app loads on your phone

---

## 📁 Project Structure

```
UniConvertor/
├── app.py                  # Flask backend & processing logic
├── static/
│   ├── index.html          # Frontend UI (Tailwind + Vanilla JS)
│   └── assets/
│       └── hero_bg.png     # Hero background image
├── uploads/                # Temp upload folder (auto-created, git-ignored)
├── downloads/              # Temp output folder (auto-created, git-ignored)
└── android/                # Android companion app
    └── app/src/main/
        ├── java/com/example/uniconvert/
        │   ├── MainActivity.kt
        │   ├── Navigation.kt
        │   ├── ui/SetupScreen.kt   # IP entry + connectivity check
        │   └── ui/WebViewScreen.kt # Full-screen WebView with file picker
        └── AndroidManifest.xml
```

---

## 🔐 Security Notes

- `werkzeug.secure_filename` sanitises all uploaded filenames
- Files are stored with a UUID prefix to prevent collisions
- Auto-cleanup thread deletes files older than 2 minutes
- `usesCleartextTraffic` is enabled in the APK only for local network use

---

## 📄 License

MIT — free to use, modify, and distribute.
