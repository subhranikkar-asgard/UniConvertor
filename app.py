import os
import uuid
import threading
import time
import zipfile
import io
import base64
import json

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
COMPRESS_LEVELS = {
    'maximum': {
        'label':       'Maximum Compression',
        'description': 'Smallest file size, reduced quality',
        'img_quality': 25,
        'img_max_dim': 800,
        'pdf_dpi':     0.7,
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
        'img_max_dim': None,
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
        actions.append({'value': 'compress_image', 'label': 'Compress Image', 'group': 'compress', 'type': 'compress'})
        for fmt in IMAGE_CONVERT_TARGETS:
            if fmt == src or (fmt == 'jpg' and src == 'jpeg') or (fmt == 'jpeg' and src == 'jpg'):
                continue
            actions.append({'value': f'img_to_{fmt}', 'label': f'Convert to {fmt.upper()}', 'group': 'convert', 'type': 'convert'})

    elif category == 'pdf':
        actions.append({'value': 'compress_pdf', 'label': 'Compress PDF', 'group': 'compress', 'type': 'compress'})
        for fmt in PDF_CONVERT_TARGETS:
            actions.append({'value': f'pdf_to_{fmt}', 'label': f'Convert to {fmt.upper()}' + (' (.docx)' if fmt == 'docx' else ''), 'group': 'convert', 'type': 'convert'})

    elif category == 'document':
        actions.append({'value': 'compress_doc', 'label': 'Compress Document', 'group': 'compress', 'type': 'compress'})
        for fmt in DOC_CONVERT_TARGETS:
            actions.append({'value': f'doc_to_{fmt}', 'label': f'Convert to {fmt.upper()}', 'group': 'convert', 'type': 'convert'})

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

# ── Helper: save uploaded PDF and return path ──────────────────────────────────
def save_upload(file_obj, delay=600):
    filename  = secure_filename(file_obj.filename)
    uid       = uuid.uuid4().hex
    path      = os.path.join(UPLOAD_FOLDER, f'{uid}_{filename}')
    file_obj.save(path)
    schedule_deletion(path, delay=delay)
    return path, uid, filename

def save_output(doc, stem, suffix, ext):
    uid   = uuid.uuid4().hex
    oname = f'{stem}_{suffix}.{ext}'
    opath = os.path.join(DOWNLOAD_FOLDER, f'{uid}_{oname}')
    doc.save(opath, garbage=4, deflate=True)
    doc.close()
    schedule_deletion(opath, delay=120)
    return opath, oname

def parse_page_list(page_str, total):
    """Parse '1,3,5-7' → sorted list of 0-indexed page numbers."""
    pages = set()
    for part in page_str.split(','):
        part = part.strip()
        if '-' in part:
            a, b = part.split('-', 1)
            pages.update(range(int(a) - 1, int(b)))
        elif part.isdigit():
            pages.add(int(part) - 1)
    return sorted(p for p in pages if 0 <= p < total)

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

    if action == 'compress_image':
        return _compress_image(upload_path, original_name, uid, cfg)
    if action.startswith('img_to_'):
        return _image_to_format(upload_path, original_name, uid, action[len('img_to_'):])
    if action == 'compress_pdf':
        return _compress_pdf(upload_path, original_name, uid, cfg)
    if action.startswith('pdf_to_'):
        target = action[len('pdf_to_'):]
        if target == 'docx':
            return _pdf_to_word(upload_path, original_name, uid)
        return _pdf_to_image(upload_path, original_name, uid, target)
    if action == 'compress_doc':
        return _compress_docx(upload_path, original_name, uid)
    if action.startswith('doc_to_'):
        target = action[len('doc_to_'):]
        if target == 'pdf':
            return _word_to_pdf(upload_path, original_name, uid)
        return _doc_to_image(upload_path, original_name, uid, target)

    raise ValueError(f'Unknown action: {action}')


# ── Image helpers ──────────────────────────────────────────────────────────────

def _ensure_rgb(img):
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
    if pil_fmt in ('JPEG', 'BMP', 'PDF'):
        img = _ensure_rgb(img)
    if pil_fmt == 'GIF' and img.mode not in ('P', 'PA', 'L', 'LA'):
        img = img.convert('P')
    if pil_fmt == 'ICO':
        img = img.convert('RGBA')
        img.thumbnail((256, 256), Image.LANCZOS)
    ext_out = 'jpg' if target in ('jpg', 'jpeg') else target
    oname   = f'{stem}_converted.{ext_out}'
    opath   = os.path.join(DOWNLOAD_FOLDER, f'{uid}_{oname}')
    kwargs  = {}
    if pil_fmt == 'JPEG':  kwargs = {'quality': 92, 'optimize': True}
    elif pil_fmt == 'WEBP': kwargs = {'quality': 90}
    elif pil_fmt == 'PDF':  kwargs = {'resolution': 150}
    img.save(opath, pil_fmt, **kwargs)
    return opath, oname


# ── PDF helpers ────────────────────────────────────────────────────────────────

def _compress_pdf(upload_path, original_name, uid, cfg):
    import fitz
    doc     = fitz.open(upload_path)
    out_doc = fitz.open()
    scale   = cfg['pdf_dpi']
    quality = cfg['pdf_quality']
    for page in doc:
        mat       = fitz.Matrix(scale, scale)
        pix       = page.get_pixmap(matrix=mat, alpha=False)
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
    from pdf2docx import Converter as PDFConverter
    stem  = original_name.rsplit('.', 1)[0]
    oname = f'{stem}_converted.docx'
    opath = os.path.join(DOWNLOAD_FOLDER, f'{uid}_{oname}')
    cv = PDFConverter(upload_path)
    cv.convert(opath, start=0, end=None)
    cv.close()
    return opath, oname


def _pdf_to_image(upload_path, original_name, uid, target):
    import fitz
    PIL_FMT = {'png': ('PNG', 'png'), 'jpg': ('JPEG', 'jpg'), 'tiff': ('TIFF', 'tiff')}
    pil_fmt, ext_out = PIL_FMT.get(target, ('PNG', 'png'))
    doc   = fitz.open(upload_path)
    pages = len(doc)
    stem  = original_name.rsplit('.', 1)[0]
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
    oname = f'{stem}_pages.zip'
    opath = os.path.join(DOWNLOAD_FOLDER, f'{uid}_{oname}')
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
    stem  = original_name.rsplit('.', 1)[0]
    oname = f'{stem}_compressed.docx'
    opath = os.path.join(DOWNLOAD_FOLDER, f'{uid}_{oname}')
    with zipfile.ZipFile(upload_path, 'r') as zin:
        with zipfile.ZipFile(opath, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zout:
            for item in zin.infolist():
                zout.writestr(item, zin.read(item.filename))
    return opath, oname


def _word_to_pdf(upload_path, original_name, uid):
    from docx2pdf import convert as docx2pdf_convert
    stem  = original_name.rsplit('.', 1)[0]
    oname = f'{stem}_converted.pdf'
    opath = os.path.join(DOWNLOAD_FOLDER, f'{uid}_{oname}')
    docx2pdf_convert(upload_path, opath)
    return opath, oname


def _doc_to_image(upload_path, original_name, uid, target):
    tmp_uid  = uuid.uuid4().hex
    pdf_name = secure_filename(original_name.rsplit('.', 1)[0] + '_tmp.pdf')
    pdf_path = os.path.join(UPLOAD_FOLDER, f'{tmp_uid}_{pdf_name}')
    from docx2pdf import convert as docx2pdf_convert
    docx2pdf_convert(upload_path, pdf_path)
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
    parts    = safe_name.split('_', 1)
    friendly = parts[1] if len(parts) > 1 else safe_name
    return send_from_directory(DOWNLOAD_FOLDER, safe_name, as_attachment=True, download_name=friendly)


# ═══════════════════════════════════════════════════════════════════════════════
#  PDF TOOLS API
# ═══════════════════════════════════════════════════════════════════════════════

def _open_fitz():
    try:
        import fitz
        return fitz
    except ImportError:
        raise ImportError('PyMuPDF not installed. Run: pip install pymupdf')


@app.route('/api/pdf/info', methods=['POST'])
def pdf_info():
    """Return page count and dimensions; keeps file in uploads for editing session."""
    fitz = _open_fitz()
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    upload_path, uid, filename = save_upload(request.files['file'], delay=600)
    try:
        doc   = fitz.open(upload_path)
        pages = [{'index': i, 'width': round(p.rect.width, 2), 'height': round(p.rect.height, 2)}
                 for i, p in enumerate(doc)]
        count = len(doc)
        doc.close()
        return jsonify({'page_count': count, 'pages': pages, 'uid': uid, 'filename': filename})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pdf/render-page', methods=['POST'])
def pdf_render_page():
    """Render one PDF page as base64 PNG. Accepts uid+filename OR a fresh file upload."""
    fitz  = _open_fitz()
    uid      = request.form.get('uid', '')
    filename = request.form.get('filename', '')
    page_num = int(request.form.get('page', 0))
    scale    = float(request.form.get('scale', 1.5))

    upload_path = None
    if uid and filename:
        candidate = os.path.join(UPLOAD_FOLDER, f'{uid}_{secure_filename(filename)}')
        if os.path.exists(candidate):
            upload_path = candidate

    if not upload_path:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        upload_path, uid, filename = save_upload(request.files['file'], delay=600)

    try:
        doc  = fitz.open(upload_path)
        if page_num >= len(doc):
            doc.close()
            return jsonify({'error': 'Page index out of range'}), 400
        page = doc[page_num]
        pw, ph = page.rect.width, page.rect.height
        mat  = fitz.Matrix(scale, scale)
        pix  = page.get_pixmap(matrix=mat, alpha=False)
        b64  = base64.b64encode(pix.tobytes('png')).decode()
        doc.close()
        return jsonify({
            'image':      f'data:image/png;base64,{b64}',
            'canvas_w':   pix.width,
            'canvas_h':   pix.height,
            'pdf_w':      pw,
            'pdf_h':      ph,
            'scale':      scale,
            'uid':        uid,
            'filename':   filename,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pdf/merge', methods=['POST'])
def pdf_merge():
    """Merge multiple PDF files into one."""
    fitz = _open_fitz()
    files = request.files.getlist('files[]')
    if len(files) < 2:
        return jsonify({'error': 'At least 2 PDF files required'}), 400
    out   = fitz.open()
    stems = []
    paths = []
    try:
        for f in files:
            path, uid, fname = save_upload(f, delay=120)
            paths.append(path)
            stems.append(fname.rsplit('.', 1)[0])
            src = fitz.open(path)
            out.insert_pdf(src)
            src.close()
        ouid  = uuid.uuid4().hex
        oname = 'merged.pdf'
        opath = os.path.join(DOWNLOAD_FOLDER, f'{ouid}_{oname}')
        out.save(opath, garbage=4, deflate=True)
        out.close()
        schedule_deletion(opath, delay=120)
        return jsonify({'download_url': f'/api/download/{ouid}_{oname}', 'filename': oname})
    except Exception as e:
        out.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/pdf/split', methods=['POST'])
def pdf_split():
    """Split PDF by page ranges like '1-3,5,7-9'. Each range → separate PDF in a ZIP."""
    fitz = _open_fitz()
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    ranges_str = request.form.get('ranges', '')
    upload_path, uid, filename = save_upload(request.files['file'], delay=120)
    stem = filename.rsplit('.', 1)[0]
    try:
        doc   = fitz.open(upload_path)
        total = len(doc)
        # Parse ranges
        range_parts = [r.strip() for r in ranges_str.split(',') if r.strip()]
        if not range_parts:
            range_parts = [f'1-{total}']
        # Build list of (start, end) 0-indexed inclusive
        segments = []
        for rp in range_parts:
            if '-' in rp:
                a, b = rp.split('-', 1)
                segments.append((max(0, int(a)-1), min(total-1, int(b)-1)))
            elif rp.isdigit():
                p = int(rp) - 1
                if 0 <= p < total:
                    segments.append((p, p))

        if len(segments) == 1:
            s, e = segments[0]
            sub  = fitz.open()
            sub.insert_pdf(doc, from_page=s, to_page=e)
            ouid  = uuid.uuid4().hex
            oname = f'{stem}_p{s+1}-{e+1}.pdf'
            opath = os.path.join(DOWNLOAD_FOLDER, f'{ouid}_{oname}')
            sub.save(opath, garbage=4, deflate=True)
            sub.close()
            doc.close()
            schedule_deletion(opath, delay=120)
            return jsonify({'download_url': f'/api/download/{ouid}_{oname}', 'filename': oname})

        ouid  = uuid.uuid4().hex
        oname = f'{stem}_split.zip'
        opath = os.path.join(DOWNLOAD_FOLDER, f'{ouid}_{oname}')
        with zipfile.ZipFile(opath, 'w', zipfile.ZIP_DEFLATED) as zf:
            for i, (s, e) in enumerate(segments):
                sub = fitz.open()
                sub.insert_pdf(doc, from_page=s, to_page=e)
                buf = io.BytesIO()
                sub.save(buf, garbage=4, deflate=True)
                zf.writestr(f'{stem}_part{i+1}_p{s+1}-{e+1}.pdf', buf.getvalue())
                sub.close()
        doc.close()
        schedule_deletion(opath, delay=120)
        return jsonify({'download_url': f'/api/download/{ouid}_{oname}', 'filename': oname})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pdf/delete-pages', methods=['POST'])
def pdf_delete_pages():
    """Delete specified pages (1-indexed) from PDF."""
    fitz = _open_fitz()
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    pages_str   = request.form.get('pages', '')
    upload_path, uid, filename = save_upload(request.files['file'], delay=120)
    stem = filename.rsplit('.', 1)[0]
    try:
        doc    = fitz.open(upload_path)
        total  = len(doc)
        to_del = parse_page_list(pages_str, total)
        if not to_del:
            doc.close()
            return jsonify({'error': 'No valid pages specified'}), 400
        keep = [i for i in range(total) if i not in to_del]
        if not keep:
            doc.close()
            return jsonify({'error': 'Cannot delete all pages'}), 400
        doc.select(keep)
        ouid  = uuid.uuid4().hex
        oname = f'{stem}_deleted.pdf'
        opath = os.path.join(DOWNLOAD_FOLDER, f'{ouid}_{oname}')
        doc.save(opath, garbage=4, deflate=True)
        doc.close()
        schedule_deletion(opath, delay=120)
        return jsonify({'download_url': f'/api/download/{ouid}_{oname}', 'filename': oname})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pdf/extract-pages', methods=['POST'])
def pdf_extract_pages():
    """Extract specified pages into a new PDF."""
    fitz = _open_fitz()
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    pages_str   = request.form.get('pages', '')
    upload_path, uid, filename = save_upload(request.files['file'], delay=120)
    stem = filename.rsplit('.', 1)[0]
    try:
        doc   = fitz.open(upload_path)
        total = len(doc)
        keep  = parse_page_list(pages_str, total)
        if not keep:
            doc.close()
            return jsonify({'error': 'No valid pages specified'}), 400
        doc.select(keep)
        ouid  = uuid.uuid4().hex
        oname = f'{stem}_extracted.pdf'
        opath = os.path.join(DOWNLOAD_FOLDER, f'{ouid}_{oname}')
        doc.save(opath, garbage=4, deflate=True)
        doc.close()
        schedule_deletion(opath, delay=120)
        return jsonify({'download_url': f'/api/download/{ouid}_{oname}', 'filename': oname})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pdf/rotate', methods=['POST'])
def pdf_rotate():
    """Rotate pages. rotations JSON: {"0":90,"1":180} or all_angle for all pages."""
    fitz = _open_fitz()
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    rotations_json = request.form.get('rotations', '{}')
    all_angle      = request.form.get('all_angle', '')
    upload_path, uid, filename = save_upload(request.files['file'], delay=120)
    stem = filename.rsplit('.', 1)[0]
    try:
        doc       = fitz.open(upload_path)
        rotations = json.loads(rotations_json)
        for i, page in enumerate(doc):
            if all_angle:
                page.set_rotation((page.rotation + int(all_angle)) % 360)
            elif str(i) in rotations:
                page.set_rotation((page.rotation + int(rotations[str(i)])) % 360)
        ouid  = uuid.uuid4().hex
        oname = f'{stem}_rotated.pdf'
        opath = os.path.join(DOWNLOAD_FOLDER, f'{ouid}_{oname}')
        doc.save(opath, garbage=4, deflate=True)
        doc.close()
        schedule_deletion(opath, delay=120)
        return jsonify({'download_url': f'/api/download/{ouid}_{oname}', 'filename': oname})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pdf/reorder', methods=['POST'])
def pdf_reorder():
    """Reorder pages. order: comma-separated 0-indexed page numbers."""
    fitz = _open_fitz()
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    order_str   = request.form.get('order', '')
    upload_path, uid, filename = save_upload(request.files['file'], delay=120)
    stem = filename.rsplit('.', 1)[0]
    try:
        doc   = fitz.open(upload_path)
        total = len(doc)
        order = [int(x) for x in order_str.split(',') if x.strip().isdigit()]
        order = [p for p in order if 0 <= p < total]
        if len(order) != total:
            doc.close()
            return jsonify({'error': 'Order must include all page indices exactly once'}), 400
        doc.select(order)
        ouid  = uuid.uuid4().hex
        oname = f'{stem}_reordered.pdf'
        opath = os.path.join(DOWNLOAD_FOLDER, f'{ouid}_{oname}')
        doc.save(opath, garbage=4, deflate=True)
        doc.close()
        schedule_deletion(opath, delay=120)
        return jsonify({'download_url': f'/api/download/{ouid}_{oname}', 'filename': oname})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pdf/add-text', methods=['POST'])
def pdf_add_text():
    """Add text elements to PDF pages. elements JSON: list of {text,x,y,page,font_size,color,bold}."""
    fitz = _open_fitz()
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    elements_json = request.form.get('elements', '[]')
    upload_path, uid, filename = save_upload(request.files['file'], delay=120)
    stem = filename.rsplit('.', 1)[0]
    try:
        doc      = fitz.open(upload_path)
        elements = json.loads(elements_json)
        for el in elements:
            page_idx = int(el.get('page', 0))
            if page_idx >= len(doc):
                continue
            page      = doc[page_idx]
            x         = float(el.get('x', 0))
            y         = float(el.get('y', 0))
            text      = str(el.get('text', ''))
            font_size = float(el.get('font_size', 14))
            color_hex = el.get('color', '#000000').lstrip('#')
            r = int(color_hex[0:2], 16) / 255
            g = int(color_hex[2:4], 16) / 255
            b = int(color_hex[4:6], 16) / 255
            fontname  = 'helv'
            page.insert_text(
                fitz.Point(x, y + font_size),   # fitz point = baseline
                text,
                fontsize=font_size,
                fontname=fontname,
                color=(r, g, b),
            )
        ouid  = uuid.uuid4().hex
        oname = f'{stem}_edited.pdf'
        opath = os.path.join(DOWNLOAD_FOLDER, f'{ouid}_{oname}')
        doc.save(opath, garbage=4, deflate=True)
        doc.close()
        schedule_deletion(opath, delay=120)
        return jsonify({'download_url': f'/api/download/{ouid}_{oname}', 'filename': oname})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pdf/add-image', methods=['POST'])
def pdf_add_image():
    """Embed an image at a fractional position on a PDF page."""
    fitz = _open_fitz()
    if 'file' not in request.files or 'image' not in request.files:
        return jsonify({'error': 'PDF and image files required'}), 400
    # Fractional coords (0–1 of page size)
    page_idx = int(request.form.get('page', 0))
    fx       = float(request.form.get('x', 0.1))
    fy       = float(request.form.get('y', 0.1))
    fw       = float(request.form.get('w', 0.3))
    fh       = float(request.form.get('h', 0.2))
    opacity  = float(request.form.get('opacity', 1.0))

    upload_path, uid, filename = save_upload(request.files['file'], delay=120)
    img_path, iuid, ifname     = save_upload(request.files['image'],   delay=120)
    stem = filename.rsplit('.', 1)[0]
    try:
        doc  = fitz.open(upload_path)
        if page_idx >= len(doc):
            doc.close()
            return jsonify({'error': 'Page out of range'}), 400
        page = doc[page_idx]
        pw, ph = page.rect.width, page.rect.height
        rect = fitz.Rect(fx * pw, fy * ph, (fx + fw) * pw, (fy + fh) * ph)
        with open(img_path, 'rb') as f:
            img_bytes = f.read()
        page.insert_image(rect, stream=img_bytes, overlay=True)
        ouid  = uuid.uuid4().hex
        oname = f'{stem}_img_added.pdf'
        opath = os.path.join(DOWNLOAD_FOLDER, f'{ouid}_{oname}')
        doc.save(opath, garbage=4, deflate=True)
        doc.close()
        schedule_deletion(opath, delay=120)
        return jsonify({'download_url': f'/api/download/{ouid}_{oname}', 'filename': oname})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pdf/add-signature', methods=['POST'])
def pdf_add_signature():
    """Embed a base64 PNG signature onto specified PDF pages."""
    fitz = _open_fitz()
    if 'file' not in request.files:
        return jsonify({'error': 'No PDF file'}), 400
    sig_data  = request.form.get('signature', '')   # data:image/png;base64,...
    page_idxs = request.form.get('pages', '0')       # comma-separated 0-indexed
    fx        = float(request.form.get('x', 0.1))
    fy        = float(request.form.get('y', 0.7))
    fw        = float(request.form.get('w', 0.35))
    fh        = float(request.form.get('h', 0.1))

    if not sig_data:
        return jsonify({'error': 'No signature data'}), 400

    upload_path, uid, filename = save_upload(request.files['file'], delay=120)
    stem = filename.rsplit('.', 1)[0]
    try:
        # Decode base64 signature PNG
        header, b64 = sig_data.split(',', 1)
        sig_bytes   = base64.b64decode(b64)
        doc         = fitz.open(upload_path)
        total       = len(doc)
        pages       = [int(p) for p in page_idxs.split(',') if p.strip().isdigit()]
        pages       = [p for p in pages if 0 <= p < total]
        if not pages:
            pages = [0]
        for pi in pages:
            page     = doc[pi]
            pw, ph   = page.rect.width, page.rect.height
            rect     = fitz.Rect(fx * pw, fy * ph, (fx + fw) * pw, (fy + fh) * ph)
            page.insert_image(rect, stream=sig_bytes, overlay=True)
        ouid  = uuid.uuid4().hex
        oname = f'{stem}_signed.pdf'
        opath = os.path.join(DOWNLOAD_FOLDER, f'{ouid}_{oname}')
        doc.save(opath, garbage=4, deflate=True)
        doc.close()
        schedule_deletion(opath, delay=120)
        return jsonify({'download_url': f'/api/download/{ouid}_{oname}', 'filename': oname})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pdf/watermark', methods=['POST'])
def pdf_watermark():
    """Add a text watermark to every page of a PDF."""
    fitz = _open_fitz()
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    text      = request.form.get('text', 'WATERMARK')
    opacity   = float(request.form.get('opacity', 0.25))
    angle     = int(request.form.get('angle', 45))
    font_size = int(request.form.get('font_size', 60))
    color_hex = request.form.get('color', '#888888').lstrip('#')
    cr = int(color_hex[0:2], 16) / 255
    cg = int(color_hex[2:4], 16) / 255
    cb = int(color_hex[4:6], 16) / 255

    upload_path, uid, filename = save_upload(request.files['file'], delay=120)
    stem = filename.rsplit('.', 1)[0]
    try:
        doc = fitz.open(upload_path)
        for page in doc:
            pw, ph = page.rect.width, page.rect.height
            # Use a text writer with rotation
            tw = fitz.TextWriter(page.rect)
            font = fitz.Font('helv')
            # Measure text width roughly
            text_w = len(text) * font_size * 0.55
            cx = pw / 2 - text_w / 2
            cy = ph / 2
            # Apply rotation via morph
            mat = fitz.Matrix(1, 1).prerotate(angle)
            tw.append(fitz.Point(cx, cy), text, font=font, fontsize=font_size)
            tw.write_text(page, color=(cr, cg, cb), opacity=opacity, morph=(fitz.Point(pw/2, ph/2), mat))
        ouid  = uuid.uuid4().hex
        oname = f'{stem}_watermarked.pdf'
        opath = os.path.join(DOWNLOAD_FOLDER, f'{ouid}_{oname}')
        doc.save(opath, garbage=4, deflate=True)
        doc.close()
        schedule_deletion(opath, delay=120)
        return jsonify({'download_url': f'/api/download/{ouid}_{oname}', 'filename': oname})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pdf/add-page-numbers', methods=['POST'])
def pdf_add_page_numbers():
    """Add page numbers to each page at a specified position."""
    fitz = _open_fitz()
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    position  = request.form.get('position', 'bottom-center')   # bottom-center|bottom-right|bottom-left|top-center|top-right|top-left
    fmt       = request.form.get('format', 'Page {n} of {total}')  # e.g. "{n}", "Page {n} of {total}"
    start     = int(request.form.get('start', 1))
    font_size = int(request.form.get('font_size', 11))
    margin    = int(request.form.get('margin', 20))
    color_hex = request.form.get('color', '#333333').lstrip('#')
    cr = int(color_hex[0:2], 16) / 255
    cg = int(color_hex[2:4], 16) / 255
    cb = int(color_hex[4:6], 16) / 255

    upload_path, uid, filename = save_upload(request.files['file'], delay=120)
    stem = filename.rsplit('.', 1)[0]
    try:
        doc   = fitz.open(upload_path)
        total = len(doc)
        for i, page in enumerate(doc):
            pw, ph = page.rect.width, page.rect.height
            label  = fmt.replace('{n}', str(i + start)).replace('{total}', str(total))
            text_w = len(label) * font_size * 0.5
            # Determine position
            pos = position.lower()
            if 'bottom' in pos:
                y = ph - margin
            else:
                y = margin + font_size
            if 'center' in pos:
                x = pw / 2 - text_w / 2
            elif 'right' in pos:
                x = pw - margin - text_w
            else:
                x = margin
            page.insert_text(fitz.Point(x, y), label, fontsize=font_size, color=(cr, cg, cb))
        ouid  = uuid.uuid4().hex
        oname = f'{stem}_numbered.pdf'
        opath = os.path.join(DOWNLOAD_FOLDER, f'{ouid}_{oname}')
        doc.save(opath, garbage=4, deflate=True)
        doc.close()
        schedule_deletion(opath, delay=120)
        return jsonify({'download_url': f'/api/download/{ouid}_{oname}', 'filename': oname})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pdf/protect', methods=['POST'])
def pdf_protect():
    """Password-protect a PDF with AES-256 encryption."""
    fitz = _open_fitz()
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    open_pw  = request.form.get('open_password', '')
    owner_pw = request.form.get('owner_password', '') or (open_pw + '_owner')

    upload_path, uid, filename = save_upload(request.files['file'], delay=120)
    stem = filename.rsplit('.', 1)[0]
    try:
        doc   = fitz.open(upload_path)
        ouid  = uuid.uuid4().hex
        oname = f'{stem}_protected.pdf'
        opath = os.path.join(DOWNLOAD_FOLDER, f'{ouid}_{oname}')
        perm  = (fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY)
        doc.save(
            opath,
            encryption=fitz.PDF_ENCRYPT_AES_256,
            owner_pw=owner_pw,
            user_pw=open_pw,
            permissions=perm,
            garbage=4,
            deflate=True,
        )
        doc.close()
        schedule_deletion(opath, delay=120)
        return jsonify({'download_url': f'/api/download/{ouid}_{oname}', 'filename': oname})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pdf/unlock', methods=['POST'])
def pdf_unlock():
    """Remove password protection from a PDF."""
    fitz = _open_fitz()
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    password    = request.form.get('password', '')
    upload_path, uid, filename = save_upload(request.files['file'], delay=120)
    stem = filename.rsplit('.', 1)[0]
    try:
        doc = fitz.open(upload_path)
        if doc.needs_pass:
            ok = doc.authenticate(password)
            if not ok:
                doc.close()
                return jsonify({'error': 'Wrong password'}), 403
        ouid  = uuid.uuid4().hex
        oname = f'{stem}_unlocked.pdf'
        opath = os.path.join(DOWNLOAD_FOLDER, f'{ouid}_{oname}')
        doc.save(opath, encryption=fitz.PDF_ENCRYPT_NONE, garbage=4, deflate=True)
        doc.close()
        schedule_deletion(opath, delay=120)
        return jsonify({'download_url': f'/api/download/{ouid}_{oname}', 'filename': oname})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pdf/flatten', methods=['POST'])
def pdf_flatten():
    """Flatten interactive form fields — makes PDF read-only."""
    fitz = _open_fitz()
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    upload_path, uid, filename = save_upload(request.files['file'], delay=120)
    stem = filename.rsplit('.', 1)[0]
    try:
        doc = fitz.open(upload_path)
        for page in doc:
            for widget in page.widgets() or []:
                widget.update()
            page.clean_contents()
        # Re-open and strip widgets by rendering to flat images
        out = fitz.open()
        for page in doc:
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img_bytes = pix.tobytes('jpeg', jpg_quality=90)
            img_pdf   = fitz.open('pdf', fitz.open('', img_bytes).convert_to_pdf())
            out.insert_pdf(img_pdf)
        ouid  = uuid.uuid4().hex
        oname = f'{stem}_flattened.pdf'
        opath = os.path.join(DOWNLOAD_FOLDER, f'{ouid}_{oname}')
        out.save(opath, garbage=4, deflate=True)
        doc.close(); out.close()
        schedule_deletion(opath, delay=120)
        return jsonify({'download_url': f'/api/download/{ouid}_{oname}', 'filename': oname})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pdf/extract-text', methods=['POST'])
def pdf_extract_text():
    """Extract all text from a PDF as a plain text file."""
    fitz = _open_fitz()
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    upload_path, uid, filename = save_upload(request.files['file'], delay=120)
    stem = filename.rsplit('.', 1)[0]
    try:
        doc   = fitz.open(upload_path)
        lines = []
        for i, page in enumerate(doc):
            lines.append(f'--- Page {i+1} ---')
            lines.append(page.get_text('text'))
            lines.append('')
        doc.close()
        content = '\n'.join(lines)
        ouid    = uuid.uuid4().hex
        oname   = f'{stem}_text.txt'
        opath   = os.path.join(DOWNLOAD_FOLDER, f'{ouid}_{oname}')
        with open(opath, 'w', encoding='utf-8') as fout:
            fout.write(content)
        schedule_deletion(opath, delay=120)
        return jsonify({
            'download_url': f'/api/download/{ouid}_{oname}',
            'filename':     oname,
            'preview':      content[:2000],
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pdf/crop', methods=['POST'])
def pdf_crop():
    """Crop each page by setting its cropbox (margins in points from each edge)."""
    fitz = _open_fitz()
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    top    = float(request.form.get('top',    0))
    right  = float(request.form.get('right',  0))
    bottom = float(request.form.get('bottom', 0))
    left   = float(request.form.get('left',   0))
    upload_path, uid, filename = save_upload(request.files['file'], delay=120)
    stem = filename.rsplit('.', 1)[0]
    try:
        doc = fitz.open(upload_path)
        for page in doc:
            r  = page.rect
            cb = fitz.Rect(r.x0 + left, r.y0 + top, r.x1 - right, r.y1 - bottom)
            page.set_cropbox(cb)
        ouid  = uuid.uuid4().hex
        oname = f'{stem}_cropped.pdf'
        opath = os.path.join(DOWNLOAD_FOLDER, f'{ouid}_{oname}')
        doc.save(opath, garbage=4, deflate=True)
        doc.close()
        schedule_deletion(opath, delay=120)
        return jsonify({'download_url': f'/api/download/{ouid}_{oname}', 'filename': oname})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)
