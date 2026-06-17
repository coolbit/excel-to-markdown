<!-- 语言 / Language: [English](README.md) · **中文** -->

# excel-to-markdown

`xlsx-to-markdown` [Claude Code](https://claude.com/claude-code) **技能（skill）的 npx 安装器**。
该技能把**文字、图片、截图、流程/泳道图混排的多 tab Excel 工作簿**转换成**保真 Markdown**：

- **每个 sheet 一张 Excel 同等保真的 PNG**（100% 等倍渲染，不模糊、不被分页切断）；
- 单元格文字以**可搜索的 Markdown** 放在每张图下方（删除线保留为 `<del>`，振假名已去除）。

## 安装技能

```bash
# 装到 ~/.claude/skills（全局）
npx github:coolbit/excel-to-markdown

# 或装到当前项目：./.claude/skills
npx github:coolbit/excel-to-markdown --project
```

安装后重启 Claude Code（或开新会话）让它发现技能。之后直接说：
*“把这个 .xlsx 转成 markdown”*、*“图片太糊/被切断了，帮我渲染这个表格”* 等，Claude 会自动触发该技能。

## 运行依赖

技能会调用三个命令行工具，外加 python3：

```bash
brew install poppler imagemagick        # pdftoppm + magick
```

**LibreOffice**（`soffice`）——先试 `brew install --cask libreoffice`。若因 macOS 版本报错
（新系统上 cask 元数据过期），改装官方 dmg：

```bash
V=$(curl -fsSL https://download.documentfoundation.org/libreoffice/stable/ \
    | grep -oE '[0-9]+\.[0-9]+\.[0-9]+/' | sort -V | tail -1 | tr -d /)
# aarch64 = Apple Silicon；Intel 用 x86-64
curl -fL -o /tmp/LO.dmg \
  "https://download.documentfoundation.org/libreoffice/stable/$V/mac/aarch64/LibreOffice_${V}_MacOS_aarch64.dmg"
hdiutil attach /tmp/LO.dmg -nobrowse -quiet
cp -R "/Volumes/LibreOffice/LibreOffice.app" ~/Applications/   # /Applications 需管理员权限
hdiutil detach "/Volumes/LibreOffice" -quiet
xattr -dr com.apple.quarantine ~/Applications/LibreOffice.app
```

## 不经 Claude 直接运行

技能里的脚本本身就是个独立命令行工具：

```bash
python3 ~/.claude/skills/xlsx-to-markdown/scripts/xlsx_to_md.py "report.xlsx" out [--dpi 200]
# → out/report.md  +  out/render/tab1.png … tabN.png
```

## 为什么需要专门的工具？

流程图的含义在于它的**二维布局 + 箭头 + 标签**——把内嵌的小图一张张抠出来就丢了这层信息。
而常见的「把整张表缩到一页」会**缩小**内嵌截图导致模糊，而且**单纯提高 DPI 也救不回来**：

| 内容 | 类型 | 提高 DPI 的效果 |
| --- | --- | --- |
| 文字、箭头、形状 | 矢量 | 越来越锐利，无上限 |
| 内嵌截图 | 位图（源像素固定） | 只是插值放大 → 依旧模糊 |

保真来自**按 100% 等倍渲染（不缩放）+ 页面足够大保证不被切断 + 裁掉白边**，而不是堆 DPI。
200 DPI 已足够覆盖原生像素，仅在需要让矢量文字更锐利时才调高。任何截图最清晰的副本，
是 xlsx 内 `xl/media/` 里的原图（这就是原生分辨率的天花板）。

## 技能工作原理

1. 解压 xlsx；读 `workbook.xml`（sheet 顺序）与 `sharedStrings.xml`。
2. 按行顺序提取每个 sheet 的文字。去掉振假名（`<rPh>`）；删除线 run（`<strike/>`）渲染为 `<del>…</del>`。
3. 给每个 sheet 注入 `<pageSetup paperWidth/Height scale="100" orientation="landscape"/>` +
   `pageSetUpPr fitToPage="0"`；重新打包。
4. `soffice --headless --convert-to pdf` —— 每个 sheet 一张大页面，不被切断。
5. 用 `magick -trim` 探测每页内容尺寸，再用 `pdftoppm` 按目标 DPI 裁剪渲染该页，最后 `magick -trim` 去白边。
6. 输出 Markdown：每个 tab → 图片 + 可折叠的提取文字。

## 许可证

MIT
