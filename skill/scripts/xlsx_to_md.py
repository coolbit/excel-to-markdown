#!/usr/bin/env python3
"""
Convert a multi-tab Excel workbook (text + embedded images + flow diagrams)
into faithful Markdown: one Excel-fidelity PNG per sheet + searchable extracted
text (strikethrough preserved).

Key idea (why output is crisp): render at 100% scale (NO fit-to-page), on a
huge custom page so nothing is split, then trim whitespace. Fidelity comes from
"native scale + no downscaling", NOT from cranking DPI. Cranking DPI cannot add
detail that the embedded raster screenshots don't have.

Usage:
  python3 xlsx_to_md.py INPUT.xlsx OUTDIR [--dpi 200] [--soffice PATH]

Deps: LibreOffice (soffice), poppler (pdftoppm), ImageMagick (magick).
Stdlib only otherwise.
"""
import argparse, os, re, shutil, subprocess, sys, tempfile, zipfile
from xml.etree import ElementTree as ET

M   = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
A   = 'http://schemas.openxmlformats.org/drawingml/2006/main'
XDR = 'http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing'

def find_soffice(explicit=None):
    for c in filter(None, [explicit, shutil.which('soffice'), shutil.which('libreoffice'),
                           '/Applications/LibreOffice.app/Contents/MacOS/soffice',
                           os.path.expanduser('~/Applications/LibreOffice.app/Contents/MacOS/soffice')]):
        if os.path.exists(c):
            return c
    sys.exit("ERROR: LibreOffice (soffice) not found. See SKILL.md install section.")

def need(tool):
    if not shutil.which(tool):
        sys.exit(f"ERROR: '{tool}' not found. Install poppler (pdftoppm) and imagemagick (magick).")

# ---------- text extraction (strikethrough -> <del>, drop furigana rPh) ----------
def run_text(r):
    t = r.find(f'{{{M}}}t'); txt = t.text if t is not None else ''
    if not txt: return ''
    rpr = r.find(f'{{{M}}}rPr')
    if rpr is not None and rpr.find(f'{{{M}}}strike') is not None:
        return f'<del>{txt}</del>'
    return txt

def si_text(si):
    parts = []
    for ch in si:
        tag = ch.tag.split('}')[1]
        if tag == 'rPh':   continue            # phonetic furigana
        if tag == 't' and ch.text: parts.append(ch.text)
        elif tag == 'r':   parts.append(run_text(ch))
    return ''.join(parts)

def colrow(ref):
    m = re.match(r'([A-Z]+)(\d+)', ref)
    if not m: return (0, 0)
    c = 0
    for ch in m.group(1): c = c*26 + (ord(ch)-64)
    return (int(m.group(2)), c)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input'); ap.add_argument('outdir')
    ap.add_argument('--dpi', type=int, default=200)
    ap.add_argument('--soffice', default=None)
    ap.add_argument('--paper-mm', type=int, default=3000, help='custom page size (each side)')
    args = ap.parse_args()

    soffice = find_soffice(args.soffice)
    need('pdftoppm'); need('magick')

    outdir = os.path.abspath(args.outdir)
    render = os.path.join(outdir, 'render')
    os.makedirs(render, exist_ok=True)
    work = tempfile.mkdtemp(prefix='xlsx2md_')
    src  = os.path.join(work, 'src');  os.makedirs(src)

    with zipfile.ZipFile(args.input) as z:
        z.extractall(src)

    # sheet order + names
    wb = open(os.path.join(src, 'xl/workbook.xml'), encoding='utf-8').read()
    sheets = [(m.group(1), m.group(2)) for m in
              re.finditer(r'<sheet [^>]*name="([^"]+)"[^>]*r:id="([^"]+)"', wb)]
    rels = open(os.path.join(src, 'xl/_rels/workbook.xml.rels'), encoding='utf-8').read()
    rid2t = {m.group(1): m.group(2) for m in
             re.finditer(r'Id="([^"]+)"[^>]*Target="([^"]+)"', rels)}

    ss = [si_text(si) for si in
          ET.parse(os.path.join(src, 'xl/sharedStrings.xml')).getroot()] \
         if os.path.exists(os.path.join(src, 'xl/sharedStrings.xml')) else []

    # ---- inject 100% scale + huge paper into every sheet (no fit-to-page) ----
    pm = args.paper_mm
    for n in range(1, len(sheets)+1):
        p = os.path.join(src, f'xl/worksheets/sheet{n}.xml')
        if not os.path.exists(p): continue
        s = open(p, encoding='utf-8').read()
        if '<sheetPr' not in s:
            s = re.sub(r'(<worksheet\b[^>]*>)',
                       r'\1<sheetPr><pageSetUpPr fitToPage="0"/></sheetPr>', s, count=1)
        ps = f'<pageSetup paperWidth="{pm}mm" paperHeight="{pm}mm" scale="100" orientation="landscape"/>'
        if '<pageSetup' in s:
            s = re.sub(r'<pageSetup[^>]*/>', ps, s, count=1)
        else:
            s = re.sub(r'(<pageMargins\b[^>]*/>)', r'\1'+ps, s, count=1)
        open(p, 'w', encoding='utf-8').write(s)

    # ---- re-zip ----
    fit = os.path.join(work, 'fit.xlsx')
    with zipfile.ZipFile(fit, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(src):
            for f in files:
                full = os.path.join(root, f)
                z.write(full, os.path.relpath(full, src))

    # ---- convert to PDF ----
    profile = os.path.join(work, 'profile')
    subprocess.run([soffice, '--headless', '--norestore',
                    f'-env:UserInstallation=file://{profile}',
                    '--convert-to', 'pdf', '--outdir', work, fit],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pdf = os.path.join(work, 'fit.pdf')
    if not os.path.exists(pdf):
        sys.exit("ERROR: LibreOffice did not produce a PDF.")

    # ---- probe content size per page at 50 dpi (trim bbox) ----
    probe = os.path.join(work, 'probe'); os.makedirs(probe)
    subprocess.run(['pdftoppm', '-png', '-r', '50', pdf, os.path.join(probe, 'p')],
                   check=True)
    pages = sorted(f for f in os.listdir(probe) if f.endswith('.png'))

    def trim_dims(png):
        out = subprocess.run(['magick', png, '-trim', 'info:-'],
                             capture_output=True, text=True).stdout
        m = re.search(r' (\d+)x(\d+)\+', out) or re.search(r'(\d+)x(\d+)', out)
        return (int(m.group(1)), int(m.group(2))) if m else (0, 0)

    # ---- render each page at target dpi, cropped to content, then trim ----
    scale = args.dpi / 50.0
    lm = int(0.7*args.dpi); tm = int(0.75*args.dpi); pad = args.dpi  # margins + pad
    img_names = []
    for i, pg in enumerate(pages, 1):
        w50, h50 = trim_dims(os.path.join(probe, pg))
        cw = int(w50*scale) + lm + pad
        ch = int(h50*scale) + tm + pad
        raw = os.path.join(work, f'raw{i}')
        subprocess.run(['pdftoppm', '-png', '-r', str(args.dpi), '-f', str(i), '-l', str(i),
                        '-x', '0', '-y', '0', '-W', str(cw), '-H', str(ch), pdf, raw],
                       check=True)
        rawpng = next(os.path.join(work, f) for f in os.listdir(work)
                      if f.startswith(f'raw{i}') and f.endswith('.png'))
        dst = os.path.join(render, f'tab{i}.png')
        subprocess.run(['magick', rawpng, '-trim', '+repage', dst], check=True)
        img_names.append(f'tab{i}.png')

    # ---- build markdown ----
    title = os.path.splitext(os.path.basename(args.input))[0]
    md = [f'# {title}\n',
          '> 各タブ = 100%等倍レンダリング(縮小なし)のPNG + 検索用抽出テキスト(取り消し線は `<del>`)。\n']
    for idx, (name, rid) in enumerate(sheets, 1):
        md.append(f'\n---\n\n## Tab{idx}: {name}\n')
        if idx <= len(img_names):
            md.append(f'![Tab{idx}: {name}](render/{img_names[idx-1]})\n')
        target = rid2t.get(rid, '')
        sp = os.path.join(src, 'xl', target)
        cells = []
        if target and os.path.exists(sp):
            for c in ET.parse(sp).getroot().iter(f'{{{M}}}c'):
                v = c.find(f'{{{M}}}v')
                if v is None or v.text is None: continue
                val = ss[int(v.text)] if c.get('t') == 's' and ss else v.text
                if val and val.strip():
                    r, co = colrow(c.get('r')); cells.append((r, co, val.strip()))
        cells.sort()
        if cells:
            md.append('\n<details><summary>📝 抽出テキスト（検索・コピー用）</summary>\n')
            md += [f'{v}  ' for _, _, v in cells]
            md.append('\n</details>\n')
        else:
            md.append('\n_（文字データなし・画像のみ）_\n')

    mdpath = os.path.join(outdir, f'{title}.md')
    open(mdpath, 'w', encoding='utf-8').write('\n'.join(md))
    shutil.rmtree(work, ignore_errors=True)
    print(f'OK -> {mdpath}')
    print(f'     images: {render} ({len(img_names)} sheets)')

if __name__ == '__main__':
    main()
