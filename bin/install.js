#!/usr/bin/env node
'use strict';

// Installs the `xlsx-to-markdown` Claude Code skill into a skills directory.
//   npx github:coolbit/excel-to-markdown            -> ~/.claude/skills/
//   npx github:coolbit/excel-to-markdown --project  -> ./.claude/skills/
//   npx github:coolbit/excel-to-markdown --dir PATH -> PATH/

const fs = require('fs');
const os = require('os');
const path = require('path');

const SKILL_NAME = 'xlsx-to-markdown';
const args = process.argv.slice(2);

if (args.includes('-h') || args.includes('--help')) {
  console.log(`Install the "${SKILL_NAME}" Claude Code skill.

Usage:
  npx github:coolbit/excel-to-markdown [--project | --dir <path>]

  (default)    install to ~/.claude/skills/${SKILL_NAME}
  --project    install to ./.claude/skills/${SKILL_NAME}
  --dir <path> install into <path>/${SKILL_NAME}

After install, Claude Code auto-discovers the skill. It needs python3 +
LibreOffice (soffice) + poppler (pdftoppm) + ImageMagick (magick) at run time.`);
  process.exit(0);
}

let base;
const dirIdx = args.indexOf('--dir');
if (dirIdx !== -1 && args[dirIdx + 1]) {
  base = path.resolve(args[dirIdx + 1]);
} else if (args.includes('--project')) {
  base = path.join(process.cwd(), '.claude', 'skills');
} else {
  base = path.join(os.homedir(), '.claude', 'skills');
}

const srcSkill = path.join(__dirname, '..', 'skills', SKILL_NAME);
const dest = path.join(base, SKILL_NAME);

try {
  fs.mkdirSync(base, { recursive: true });
  fs.rmSync(dest, { recursive: true, force: true });   // clean reinstall
  fs.cpSync(srcSkill, dest, { recursive: true });
  const py = path.join(dest, 'scripts', 'xlsx_to_md.py');
  if (fs.existsSync(py)) fs.chmodSync(py, 0o755);
} catch (e) {
  console.error(`ERROR installing skill: ${e.message}`);
  process.exit(1);
}

console.log(`✓ Installed skill "${SKILL_NAME}" -> ${dest}`);
console.log(`  Restart Claude Code (or start a new session) so it discovers the skill.`);
console.log(`  Runtime deps: python3, LibreOffice (soffice), poppler (pdftoppm), ImageMagick (magick).`);
console.log(`    brew install poppler imagemagick   # + LibreOffice (see README)`);
