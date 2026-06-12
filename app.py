import os
import uuid
import threading
import time
import zipfile
import io

from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__, static_folder='static', static_url_path='/static')

# ── Configuration ──────────────────────────────────────────────────────────────
UPLOAD_FOLDER   = os.path.join(os.path.dirname(__file__), 'uploads')
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'downloads')
MAX_CONTENT_LENGTH = 100 * 1024 * 1024   # 100 MB

app.config['UPLOAD_FOLDER']      = UPLOAD_FOLDER
app.config['DOWNLOAD_FOLDER']    = DOWNLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

os.makedirs(UPLOAD_FOLDER,   exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# ── File type registry ─────────────────────────────────────────────────────────
IMAGE_EXTS    = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff', 'tif', 'ico'}
PDF_EXTS      = {'pdf'}
DOCUMENT_EXTS = {'docx', 'doc'}

def get_file_category(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext in IMAGE_EXTS:    return 'image', ext
    if ext in PDF_EXTS:      return 'pdf',   ext
    if ext in DOCUMENT_EXTS: return 'document', ext
    return None, ext

# ── Compression level definitions ──────────────────────────────────────────────
# Each level controls: image JPEG quality, max dimension, PDF render DPI, PDF JPEG quality
COMPRESS_LEVELS = {
    'maximum': {
        'label':       'Maximum Compression',
        'description': 'Smallest file size, reduced quality',
        'img_quality': 25,
        'img_max_dim': 800,
        'pdf_dpi':     0.7,    # scale factor for fitz.Matrix
        'pdf_quality': 25,
    },
    'recommended': {
        'label':       'Recommended',
        'description': 'Best balance of size and quality',
        'img_quality': 68,
        'img_max_dim': 1920,
        'pdf_dpi':     1.2,
        'pdf_quality': 60,
    },
    'minimum': {
        'label':       'Minimum Compression',
        'description': 'Near-original quality, slightly smaller',
        'img_quality': 88,
        'img_max_dim': None,   # no resize
        'pdf_dpi':     1.8,
        'pdf_quality': 82,
    },
}

# ── All possible output formats per category ──────────────────────────────────
IMAGE_CONVERT_TARGETS  = ['jpg', 'png', 'webp', 'bmp', 'gif', 'tiff', 'ico', 'pdf']
PDF_CONVERT_TARGETS    = ['docx', 'png', 'jpg', 'tiff']
DOC_CONVERT_TARGETS    = ['pdf', 'png', 'jpg']

def build_actions(category, src_ext):
    """Return action list for a given file category, excluding the source format."""
    actions = []
    src = src_ext.lower()

    if category == 'image':
        # ── Compression group ──
        actions.append({
            'value': 'compress_image',
            'label': 'Compress Image',
            'group': 'compress',
            'type':  'compress',
        })
        # ── Conversion group ──
        for fmt in IMAGE_CONVERT_TARGETS:
            if fmt == src or (fmt == 'jpg' and src == 'jpeg') or (fmt == 'jpeg' and src == 'jpg'):
                continue
            actions.append({
                'value': f'img_to_{fmt}',
                'label': f'Convert to {fmt.upper()}',
                'group': 'convert',
                'type':  'convert',
            })

    elif category == 'pdf':
        actions.append({
            'value': 'compress_pdf',
            'label': 'Compress PDF',
            'group': 'compress',
            'type':  'compress',
        })
        for fmt in PDF_CONVERT_TARGETS:
            actions.append({
                'value': f'pdf_to_{fmt}',
                'label': f'Convert to {fmt.upper()}' + (' (.docx)' if fmt == 'docx' else ''),
                'group': 'convert',
                'type':  'convert',
            })

    elif category == 'document':
        actions.append({
            'value': 'compress_doc',
            'label': 'Compress Document',
            'group': 'compress',
            'type':  'compress',
        })
        for fmt in DOC_CONVERT_TARGETS:
            actions.append({
                'value': f'doc_to_{fmt}',
                'label': f'Convert to {fmt.upper()}',
                'group': 'convert',
                'type':  'convert',
            })

    return actions

# ── Auto-deletion ──────────────────────────────────────────────────────────────
def schedule_deletion(filepath, delay=120):
    def _delete():
        time.sleep(delay)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass
    threading.Thread(target=_delete, daemon=True).start()

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/api/upload-info', methods=['POST'])
def upload_info():
    filename = request.json.get('filename', '')
    category, ext = get_file_category(filename)
    if not category:
        return jsonify({'error': f'Unsupported file type: .{ext}'}), 400

    actions = build_actions(category, ext)
    return jsonify({
        'category': category,
        'ext':      ext,
        'actions':  actions,
        'compress_levels': [
            {'value': k, 'label': v['label'], 'description': v['description']}
            for k, v in COMPRESS_LEVELS.items()
        ],
    })


@app.route('/api/process', methods=['POST'])
def process_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400

    file   = request.files['file']
    action = request.form.get('action', '')
    level  = request.form.get('compress_level', 'recommended')

    if not file or not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    original_name = secure_filename(file.filename)
    category, ext = get_file_category(original_name)

    if not category:
        return jsonify({'error': f'Unsupported file type: .{ext}'}), 400

    uid         = uuid.uuid4().hex
    upload_path = os.path.join(UPLOAD_FOLDER, f'{uid}_{original_name}')
    file.save(upload_path)

    try:
        output_path, output_name = dispatch(upload_path, original_name, action, uid, category, ext, level)
    except Exception as e:
        try: os.remove(upload_path)
        except Exception: pass
        return jsonify({'error': str(e)}), 500

    schedule_deletion(upload_path, delay=60)
    schedule_deletion(output_path, delay=120)

    download_url = f'/api/download/{os.path.basename(output_path)}'
    return jsonify({'download_url': download_url, 'filename': output_name})


# ── Dispatcher ─────────────────────────────────────────────────────────────────

def dispatch(upload_path, original_name, action, uid, category, ext, level):
    cfg = COMPRESS_LEVELS.get(level, COMPRESS_LEVELS['recommended'])

    # ── IMAGE ──────────────────────────────────────────────────────────────────
    if action == 'compress_image':
        return _compress_image(upload_path, original_name, uid, cfg)

    if action.startswith('img_to_'):
        target = action[len('img_to_'):]   # jpg / png / webp / bmp / gif / tiff / ico / pdf
        return _image_to_format(upload_path, original_name, uid, target)

    # ── PDF ────────────────────────────────────────────────────────────────────
    if action == 'compress_pdf':
        return _compress_pdf(upload_path, original_name, uid, cfg)

    if action.startswith('pdf_to_'):
        target = action[len('pdf_to_'):]   # docx / png / jpg / tiff
        if target == 'docx':
            return _pdf_to_word(upload_path, original_name, uid)
        return _pdf_to_image(upload_path, original_name, uid, target)

    # ── DOCUMENT ───────────────────────────────────────────────────────────────
    if action == 'compress_doc':
        return _compress_docx(upload_path, original_name, uid)

    if action.startswith('doc_to_'):
        target = action[len('doc_to_'):]   # pdf / png / jpg
        if target == 'pdf':
            return _word_to_pdf(upload_path, original_name, uid)
        return _doc_to_image(upload_path, original_name, uid, target)

    raise ValueError(f'Unknown action: {action}')


# ── Image helpers ──────────────────────────────────────────────────────────────

def _ensure_rgb(img):
    """Convert any mode to RGB (white background for transparent modes)."""
    if img.mode in ('RGBA', 'LA', 'P'):
        bg = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        if img.mode in ('RGBA', 'LA'):
            bg.paste(img, mask=img.split()[-1])
        return bg
    if img.mode != 'RGB':
        return img.convert('RGB')
    return img


def _compress_image(upload_path, original_name, uid, cfg):
    img = Image.open(upload_path)

    # Preserve EXIF orientation
    try:
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    img = _ensure_rgb(img)

    max_dim = cfg['img_max_dim']
    if max_dim:
        w, h = img.size
        if max(w, h) > max_dim:
            scale = max_dim / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    stem  = original_name.rsplit('.', 1)[0]
    oname = f'{stem}_compressed.jpg'
    opath = os.path.join(DOWNLOAD_FOLDER, f'{uid}_{oname}')
    img.save(opath, 'JPEG', quality=cfg['img_quality'], optimize=True)
    return opath, oname


def _image_to_format(upload_path, original_name, uid, target):
    img  = Image.open(upload_path)
    stem = original_name.rsplit('.', 1)[0]

    PIL_FMT = {
        'png': 'PNG', 'jpg': 'JPEG', 'jpeg': 'JPEG',
        'webp': 'WEBP', 'bmp': 'BMP', 'gif': 'GIF',
        'tiff': 'TIFF', 'ico': 'ICO', 'pdf': 'PDF',
    }
    pil_fmt = PIL_FMT.get(target, target.upper())

    # JPEG / BMP / PDF don't support transparency
    if pil_fmt in ('JPEG', 'BMP', 'PDF'):
        img = _ensure_rgb(img)

    # GIF: needs palette mode
    if pil_fmt == 'GIF' and img.mode not in ('P', 'PA', 'L', 'LA'):
        img = img.convert('P')

    # ICO: max 256×256
    if pil_fmt == 'ICO':
        img = img.convert('RGBA')
        img.thumbnail((256, 256), Image.LANCZOS)

    ext_out  = 'jpg' if target in ('jpg', 'jpeg') else target
    oname    = f'{stem}_converted.{ext_out}'
    opath    = os.path.join(DOWNLOAD_FOLDER, f'{uid}_{oname}')

    kwargs = {}
    if pil_fmt == 'JPEG':
        kwargs = {'quality': 92, 'optimize': True}
    elif pil_fmt == 'WEBP':
        kwargs = {'quality': 90}
    elif pil_fmt == 'PDF':
        kwargs = {'resolution': 150}

    img.save(opath, pil_fmt, **kwargs)
    return opath, oname


# ── PDF helpers ────────────────────────────────────────────────────────────────

def _compress_pdf(upload_path, original_name, uid, cfg):
    try:
        import fitz
    except ImportError:
        raise ImportError('PyMuPDF not installed. Run: pip install pymupdf')

    doc     = fitz.open(upload_path)
    out_doc = fitz.open()
    scale   = cfg['pdf_dpi']
    quality = cfg['pdf_quality']

    for page in doc:
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_bytes = pix.tobytes('jpeg', jpg_quality=quality)
        img_pdf   = fitz.open('pdf', fitz.open('', img_bytes).convert_to_pdf())
        out_doc.insert_pdf(img_pdf)

    stem  = original_name.rsplit('.', 1)[0]
    oname = f'{stem}_compressed.pdf'
    opath = os.path.join(DOWNLOAD_FOLDER, f'{uid}_{oname}')
    out_doc.save(opath, garbage=4, deflate=True)
    doc.close(); out_doc.close()
    return opath, oname


def _pdf_to_word(upload_path, original_name, uid):
    try:
        from pdf2docx import Converter as PDFConverter
    except ImportError:
        raise ImportError('pdf2docx not installed. Run: pip install pdf2docx')

    stem  = original_name.rsplit('.', 1)[0]
    oname = f'{stem}_converted.docx'
    opath = os.path.join(DOWNLOAD_FOLDER, f'{uid}_{oname}')

    cv = PDFConverter(upload_path)
    cv.convert(opath, start=0, end=None)
    cv.close()
    return opath, oname


def _pdf_to_image(upload_path, original_name, uid, target):
    """Convert each PDF page to an image. Returns ZIP if multi-page, else single image."""
    try:
        import fitz
    except ImportError:
        raise ImportError('PyMuPDF not installed. Run: pip install pymupdf')

    PIL_FMT = {'png': ('PNG', 'png'), 'jpg': ('JPEG', 'jpg'), 'tiff': ('TIFF', 'tiff')}
    pil_fmt, ext_out = PIL_FMT.get(target, ('PNG', 'png'))

    doc   = fitz.open(upload_path)
    pages = len(doc)
    stem  = original_name.rsplit('.', 1)[0]

    # Render at 150 DPI (scale=2 means ~144 DPI)
    mat   = fitz.Matrix(2, 2)

    if pages == 1:
        pix   = doc[0].get_pixmap(matrix=mat, alpha=False)
        img   = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
        oname = f'{stem}_page1.{ext_out}'
        opath = os.path.join(DOWNLOAD_FOLDER, f'{uid}_{oname}')
        kwargs = {'quality': 90, 'optimize': True} if pil_fmt == 'JPEG' else {}
        img.save(opath, pil_fmt, **kwargs)
        doc.close()
        return opath, oname

    # Multi-page → ZIP
    oname   = f'{stem}_pages.zip'
    opath   = os.path.join(DOWNLOAD_FOLDER, f'{uid}_{oname}')
    with zipfile.ZipFile(opath, 'w', zipfile.ZIP_DEFLATED) as zf:
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
            buf = io.BytesIO()
            kwargs = {'quality': 90, 'optimize': True} if pil_fmt == 'JPEG' else {}
            img.save(buf, pil_fmt, **kwargs)
            zf.writestr(f'page_{i+1:03d}.{ext_out}', buf.getvalue())

    doc.close()
    return opath, oname


# ── Document helpers ───────────────────────────────────────────────────────────

def _compress_docx(upload_path, original_name, uid):
    """Compress DOCX by re-saving with python-docx (removes redundant markup)."""
    try:
        import shutil
        stem  = original_name.rsplit('.', 1)[0]
        oname = f'{stem}_compressed.docx'
        opath = os.path.join(DOWNLOAD_FOLDER, f'{uid}_{oname}')
        # Use zipfile to repack the DOCX with maximum compression
        with zipfile.ZipFile(upload_path, 'r') as zin:
            with zipfile.ZipFile(opath, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zout:
                for item in zin.infolist():
                    zout.writestr(item, zin.read(item.filename))
        return opath, oname
    except Exception as e:
        raise RuntimeError(f'DOCX compression failed: {e}')


def _word_to_pdf(upload_path, original_name, uid):
    try:
        from docx2pdf import convert as docx2pdf_convert
    except ImportError:
        raise ImportError('docx2pdf not installed. Run: pip install docx2pdf')

    stem  = original_name.rsplit('.', 1)[0]
    oname = f'{stem}_converted.pdf'
    opath = os.path.join(DOWNLOAD_FOLDER, f'{uid}_{oname}')
    docx2pdf_convert(upload_path, opath)
    return opath, oname


def _doc_to_image(upload_path, original_name, uid, target):
    """Convert DOCX → PDF first via docx2pdf, then PDF pages → images."""
    # Step 1: DOCX → PDF
    tmp_uid  = uuid.uuid4().hex
    pdf_name = secure_filename(original_name.rsplit('.', 1)[0] + '_tmp.pdf')
    pdf_path = os.path.join(UPLOAD_FOLDER, f'{tmp_uid}_{pdf_name}')

    try:
        from docx2pdf import convert as docx2pdf_convert
        docx2pdf_convert(upload_path, pdf_path)
    except ImportError:
        raise ImportError('docx2pdf not installed. Run: pip install docx2pdf')

    # Step 2: PDF → images
    opath, oname = _pdf_to_image(pdf_path, original_name.rsplit('.', 1)[0] + '.pdf', uid, target)
    schedule_deletion(pdf_path, delay=60)
    return opath, oname


# ── Download route ─────────────────────────────────────────────────────────────

@app.route('/api/download/<path:filename>')
def download_file(filename):
    safe_name = secure_filename(filename)
    file_path = os.path.join(DOWNLOAD_FOLDER, safe_name)
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found or already deleted'}), 404

    # Strip uid prefix to restore the friendly name
    parts = safe_name.split('_', 1)
    friendly = parts[1] if len(parts) > 1 else safe_name

    return send_from_directory(
        DOWNLOAD_FOLDER, safe_name,
        as_attachment=True,
        download_name=friendly
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)
