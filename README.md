# UniConvertor 🚀

A **free, universal file converter and compressor** — convert and compress images, PDFs, and Word documents right from your browser. No sign-up. No watermarks. No limits.

---

## ✨ Features

- 🖼️ **Image conversion** — PNG ↔ JPG ↔ WebP ↔ BMP ↔ GIF ↔ TIFF ↔ ICO ↔ PDF
- 📄 **PDF tools** — Compress · Convert to Word (DOCX) · Convert to Images (ZIP)
- 📝 **Word tools** — Convert to PDF · Convert to Images (ZIP)
- 🗜️ **3 compression levels** — Maximum · Recommended · Minimum
- 🔒 **Privacy first** — files auto-deleted after 2 minutes
- ⚡ **Fast** — server-side processing, even large multi-page PDFs done in seconds
- 💸 **100% Free** — no accounts, no paywalls, forever

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

---

## 📦 Installation

### 1. Clone the repo
```bash
git clone https://github.com/subhranikkar-asgard/UniConvertor.git
cd UniConvertor
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install flask pillow pymupdf pdf2docx docx2pdf werkzeug
```

### 3. Run the server
```bash
python app.py
```

Open **http://localhost:5000** in your browser — that's it!

---

## 🔄 Supported Conversions

| Input | Compress | Convert To |
|-------|----------|------------|
| 🖼️ Images (PNG, JPG, WebP, GIF, BMP, TIFF, ICO) | ✅ Max / Recommended / Min | JPG · PNG · WebP · BMP · GIF · TIFF · ICO · PDF |
| 📄 PDF | ✅ Max / Recommended / Min | DOCX · PNG · JPG · TIFF *(multi-page → ZIP)* |
| 📝 Word (DOCX, DOC) | ✅ Re-pack | PDF · PNG · JPG *(pages → ZIP)* |

---

## 📁 Project Structure

```
UniConvertor/
├── app.py              # Flask backend & all processing logic
├── requirements.txt    # Python dependencies
├── static/
│   ├── index.html      # Frontend UI (Tailwind CSS + Vanilla JS)
│   └── assets/
│       └── hero_bg.png # Hero section background
├── uploads/            # Temp upload folder (auto-created, git-ignored)
└── downloads/          # Temp output folder (auto-created, git-ignored)
```

---

## 🔐 Security

- `werkzeug.secure_filename` sanitises all uploaded filenames
- Files stored with a UUID prefix to prevent collisions
- Auto-cleanup thread deletes files older than **2 minutes**
- 100 MB max upload size enforced on both frontend and backend

---

## 📄 License

MIT — free to use, modify, and distribute.
