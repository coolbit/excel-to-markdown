#!/usr/bin/env node
'use strict';

const { spawnSync } = require('child_process');
const path = require('path');

const args = process.argv.slice(2);

function usage() {
  console.log(`excel-to-markdown — convert a multi-tab .xlsx into faithful Markdown + per-sheet PNGs

Usage:
  npx excel-to-markdown <input.xlsx> <outdir> [options]

Options:
  --dpi <n>        render DPI (default 200; raise to 300 only to sharpen vector text)
  --paper-mm <n>   custom page size per side (default 3000; raise for very wide sheets)
  --soffice <path> explicit path to LibreOffice 'soffice' binary

Output:
  <outdir>/<name>.md          one section per tab: image + searchable text
  <outdir>/render/tab1..N.png Excel-fidelity image per sheet (100% scale, not split)

Requires: python3, LibreOffice (soffice), poppler (pdftoppm), ImageMagick (magick).
  brew install poppler imagemagick
  LibreOffice: https://www.libreoffice.org/download/download-libreoffice/
`);
}

if (args.includes('-h') || args.includes('--help')) {
  usage();
  process.exit(0);
}
if (args.length < 2) {
  usage();
  process.exit(1);
}

function hasCmd(cmd, probeArg) {
  try {
    return spawnSync(cmd, [probeArg], { stdio: 'ignore' }).status === 0;
  } catch (_) {
    return false;
  }
}

const py = hasCmd('python3', '--version') ? 'python3'
         : hasCmd('python', '--version') ? 'python'
         : null;

if (!py) {
  console.error('ERROR: python3 not found. Install Python 3 (macOS ships it; or `brew install python`).');
  process.exit(1);
}

const script = path.join(__dirname, '..', 'lib', 'xlsx_to_md.py');
const r = spawnSync(py, [script, ...args], { stdio: 'inherit' });
process.exit(r.status === null ? 1 : r.status);
