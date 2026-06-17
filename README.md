# excel-to-markdown

An **npx installer** for the `xlsx-to-markdown` [Claude Code](https://claude.com/claude-code)
skill. The skill converts a **multi-tab Excel workbook** — where text, images,
screenshots and flow/swimlane diagrams are laid out together — into **faithful
Markdown**:

- **one Excel-fidelity PNG per sheet** (rendered at 100% scale, never blurry, never
  split across page breaks), and
- the cell text as **searchable Markdown** below each image (strikethrough preserved
  as `<del>`, furigana stripped).

## Install the skill

```bash
# into ~/.claude/skills (global)
npx github:coolbit/excel-to-markdown

# or into the current project: ./.claude/skills
npx github:coolbit/excel-to-markdown --project
```

Restart Claude Code (or open a new session) so it discovers the skill. Then just ask:
*"convert this .xlsx to markdown"*, *"the images are blurry / split — render this
spreadsheet"*, etc. — Claude triggers the skill automatically.

## Runtime requirements

The skill shells out to three CLIs plus python3:

```bash
brew install poppler imagemagick        # pdftoppm + magick
```

**LibreOffice** (`soffice`) — try `brew install --cask libreoffice` first. If it fails
with a macOS-version error (stale cask on a newer OS), install the official dmg:

```bash
V=$(curl -fsSL https://download.documentfoundation.org/libreoffice/stable/ \
    | grep -oE '[0-9]+\.[0-9]+\.[0-9]+/' | sort -V | tail -1 | tr -d /)
# aarch64 = Apple Silicon; use x86-64 for Intel
curl -fL -o /tmp/LO.dmg \
  "https://download.documentfoundation.org/libreoffice/stable/$V/mac/aarch64/LibreOffice_${V}_MacOS_aarch64.dmg"
hdiutil attach /tmp/LO.dmg -nobrowse -quiet
cp -R "/Volumes/LibreOffice/LibreOffice.app" ~/Applications/   # /Applications needs admin
hdiutil detach "/Volumes/LibreOffice" -quiet
xattr -dr com.apple.quarantine ~/Applications/LibreOffice.app
```

## Run it directly (without Claude)

The skill's script is a standalone CLI:

```bash
python3 ~/.claude/skills/xlsx-to-markdown/scripts/xlsx_to_md.py "report.xlsx" out [--dpi 200]
# → out/report.md  +  out/render/tab1.png … tabN.png
```

## Why a dedicated tool?

A flow diagram's meaning lives in its **2D layout + arrows + labels** — extracting the
embedded sprite images one-by-one loses that. And the usual "fit sheet to one page"
trick **shrinks** the embedded screenshots, so they blur — and **cranking DPI does not
fix it**:

| content | type | effect of higher DPI |
| --- | --- | --- |
| text, arrows, shapes | vector | sharper, no ceiling |
| embedded screenshots | raster (fixed source pixels) | just interpolates → stays blurry |

Fidelity comes from **rendering at 100% scale (no fit-to-page) on a page large enough
that nothing splits, then trimming whitespace** — not from DPI. 200 DPI captures native
pixels; raise it only to sharpen vector text. The single sharpest copy of any screenshot
is the original in `xl/media/` inside the xlsx (the native-resolution ceiling).

## How the skill works

1. Unzip the xlsx; read `workbook.xml` (sheet order) and `sharedStrings.xml`.
2. Extract text per sheet in row order. Drop furigana (`<rPh>`); render strikethrough
   runs (`<strike/>`) as `<del>…</del>`.
3. Inject `<pageSetup paperWidth/Height scale="100" orientation="landscape"/>` +
   `pageSetUpPr fitToPage="0"` into each sheet; re-zip.
4. `soffice --headless --convert-to pdf` — one big page per sheet, nothing split.
5. Probe content size per page (`magick -trim`), then `pdftoppm` each page cropped to
   content at the target DPI and `magick -trim` the result.
6. Emit Markdown: per tab → image + collapsible extracted text.

## License

MIT
