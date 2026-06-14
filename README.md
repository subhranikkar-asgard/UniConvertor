# UniConvertor 🚀

A **free, universal file converter, compressor, and PDF editor** — all running locally in your browser. No sign-up. No watermarks. No cloud uploads.

---

## ✨ Features

### 🔄 File Converter & Compressor
- 🖼️ **Image conversion** — PNG ↔ JPG ↔ WebP ↔ BMP ↔ GIF ↔ TIFF ↔ ICO ↔ PDF
- 📄 **PDF tools** — Compress · Convert to Word (DOCX) · Convert to Images (ZIP)
- 📝 **Word tools** — Convert to PDF · Convert to Images (ZIP)
- 🗜️ **3 compression levels** — Maximum · Recommended · Minimum

### 📄 PDF Editing Suite (18 tools)

**Edit & Sign**
- 🔤 **Add Text** — click anywhere on the page to place and style text
- 🖼️ **Add Image** — embed any image, drag to position and resize
- ✍️ **Sign PDF** — draw, type, or upload a signature and place it on the PDF
- 💧 **Watermark** — add diagonal text watermarks with custom opacity and color
- 🔢 **Page Numbers** — add page numbers at any of 6 positions

**Organize Pages**
- 🔗 **Merge PDFs** — drag-to-reorder file list, then combine
- ✂️ **Split PDF** — split by page ranges (e.g. `1-3, 5, 7-9`)
- 🗑️ **Delete Pages** — visual thumbnail grid, click to select and remove
- 📤 **Extract Pages** — save only the pages you need
- 🔄 **Rotate Pages** — rotate individual pages or all at once
- 🔀 **Reorder Pages** — drag-and-drop thumbnails to rearrange
- ✂️ **Crop PDF** — trim margins in PDF points

**Security**
- 🔐 **Protect PDF** — AES-256 password encryption
- 🔓 **Unlock PDF** — remove password with known credentials
- 📋 **Flatten PDF** — make form fields non-editable, print-ready

**Convert & Extract**
- 📝 **Extract Text** — export all PDF text to a `.txt` file

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python · Flask |
| Frontend | HTML · Tailwind CSS · Vanilla JS |
| Image processing | Pillow |
| PDF processing | PyMuPDF (fitz) — handles all 18 PDF tools |
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
├── app.py              # Flask backend — converter + 18 PDF tool routes
├── requirements.txt    # Python dependencies
├── static/
│   ├── index.html      # SPA frontend — converter + PDF tools hub
│   └── assets/
│       └── hero_bg.png # Hero section background
├── uploads/            # Temp upload folder (auto-created, git-ignored)
└── downloads/          # Temp output folder (auto-created, git-ignored)
```

---

## 🔐 Security & Privacy

- All files processed **100% locally** — nothing sent to any cloud
- `werkzeug.secure_filename` sanitises all uploaded filenames
- Files stored with a UUID prefix to prevent collisions
- Auto-cleanup thread deletes files after **2 minutes**
- 100 MB max upload size enforced on both frontend and backend

---

## 📄 License

MIT — free to use, modify, and distribute.
