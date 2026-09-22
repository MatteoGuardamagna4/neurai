"""Build the D7 report from its Markdown sections into Word, and optionally PDF.

    uv run --no-project --with pypandoc-binary --with python-docx python report/build.py [--pdf]

The sections are `report/NN_*.md`, joined in name order; `<!-- ... -->` notes are dropped. The layout follows the ESADE
guidelines: A4, Arial 11 pt, single spacing with 6 pt before and after, justified, 30 mm side and 25 mm top and bottom
margins, numbered headings, page numbers at the bottom, data source at the foot of every figure and table. When
Microsoft Word is installed it then updates the index, writes the page and word count at its end, formats the tables
and, with --pdf, exports the PDF. Close the document in Word before rebuilding, or the save fails.
"""
import argparse
import datetime as dt
import re
import shutil
import subprocess
from pathlib import Path

import pypandoc
from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

HERE = Path(__file__).resolve().parent
OUT = HERE / "build"
NAME = "NeuroTutorSim_report_draft"
FONT = "Arial"
LEFT, CENTER, JUSTIFY = WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.JUSTIFY


# ------------------------------------------------------------------ source
def source_text() -> str:
    """All sections in order, notes removed, fully italic paragraphs carrying a source line styled as notes."""
    parts = [p.read_text(encoding="utf-8") for p in sorted(HERE.glob("[0-9][0-9]_*.md"))]
    text = re.sub(r"<!--.*?-->", "", "\n\n".join(parts), flags=re.S)
    blocks = re.split(r"\n\s*\n", text)
    for i, b in enumerate(blocks):
        s = b.strip()
        if s.startswith("*") and s.endswith("*") and "Source:" in s:
            blocks[i] = f'::: {{custom-style="Source"}}\n{s}\n:::'
    return "\n\n".join(blocks)


# ------------------------------------------------------------------ reference document (styles and page layout)
def _font(style, size=None, bold=None, italic=None):
    rpr = style.element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.insert(0, fonts)
    for attr in list(fonts.attrib):  # theme fonts would override the explicit face
        del fonts.attrib[attr]
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(attr), FONT)
    for el in rpr.findall(qn("w:spacing")):  # character spacing (pandoc's Subtitle has some)
        rpr.remove(el)
    if size:
        style.font.size = Pt(size)
    if bold is not None:
        style.font.bold = bold
    if italic is not None:
        style.font.italic = italic
    style.font.color.rgb = RGBColor(0, 0, 0)


def _para(style, align, before=6, after=6, keep_next=False, page_break=False, hanging=None):
    pf = style.paragraph_format
    pf.alignment, pf.line_spacing = align, 1.0
    pf.space_before, pf.space_after = Pt(before), Pt(after)
    pf.keep_with_next, pf.page_break_before = keep_next, page_break
    if hanging:
        pf.left_indent, pf.first_line_indent = Mm(hanging), -Mm(hanging)


def reference_docx(path: Path) -> None:
    default = subprocess.run([pypandoc.get_pandoc_path(), "--print-default-data-file", "reference.docx"],
                             capture_output=True, check=True).stdout
    path.write_bytes(default)
    doc = Document(path)
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Mm(210), Mm(297)
    sec.left_margin = sec.right_margin = Mm(30)
    sec.top_margin = sec.bottom_margin = Mm(25)
    footer = sec.footer.paragraphs[0]
    footer.alignment = CENTER
    for kind, text in (("begin", None), (None, " PAGE "), ("end", None)):
        run = OxmlElement("w:r")
        if kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = text
        run.append(el)
        footer._p.append(run)

    compat = doc.settings.element.find(qn("w:compat"))  # otherwise Word opens the file in compatibility mode
    if compat is None:
        compat = OxmlElement("w:compat")
        doc.settings.element.append(compat)
    for el in compat.findall(qn("w:compatSetting")):
        compat.remove(el)
    setting = OxmlElement("w:compatSetting")
    setting.set(qn("w:name"), "compatibilityMode")
    setting.set(qn("w:uri"), "http://schemas.microsoft.com/office/word")
    setting.set(qn("w:val"), "15")
    compat.append(setting)

    styles = doc.styles
    for name in ("Source", "Cover"):
        if name not in [s.name for s in styles]:
            styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH).base_style = styles["Normal"]
    body = {"Normal", "Body Text", "First Paragraph", "Block Text", "Abstract"}
    for s in styles:
        if s.type != WD_STYLE_TYPE.PARAGRAPH:
            continue
        if s.name in body:
            _font(s, 11)
            _para(s, JUSTIFY)
    _font(styles["Compact"], 11)
    _para(styles["Compact"], LEFT, 0, 3)
    for level, size, before in ((1, 14, 0), (2, 12, 12), (3, 11, 9)):
        h = styles[f"Heading {level}"]
        _font(h, size, bold=True, italic=False)
        _para(h, LEFT, before, 6, keep_next=True, page_break=level == 1)
    _font(styles["TOC Heading"], 14, bold=True, italic=False)
    _para(styles["TOC Heading"], LEFT, 0, 12, page_break=True)
    _font(styles["Title"], 22, bold=True)
    _para(styles["Title"], CENTER, 150, 12)
    for name, size in (("Subtitle", 14), ("Author", 12), ("Date", 11)):
        _font(styles[name], size, bold=False, italic=False)
        _para(styles[name], CENTER, 6, 6)
    _font(styles["Cover"], 11)
    _para(styles["Cover"], CENTER, 3, 3)
    for name in ("Table Caption", "Image Caption"):
        _font(styles[name], 10, bold=True, italic=False)
        _para(styles[name], LEFT, 12, 6, keep_next=True)
    _font(styles["Source"], 9)
    _para(styles["Source"], LEFT, 3, 12)
    _font(styles["Bibliography"], 11)
    _para(styles["Bibliography"], LEFT, 0, 6, hanging=12.7)
    doc.save(path)


# ------------------------------------------------------------------ Word post-processing
WORD_SCRIPT = r"""
param([string]$Docx, [string]$Pdf)
$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
  $doc = $word.Documents.Open($Docx)
  foreach ($t in $doc.Tables) {
    $t.Range.Font.Size = 9
    $t.Range.ParagraphFormat.Alignment = 0
    $t.Range.ParagraphFormat.SpaceBefore = 2
    $t.Range.ParagraphFormat.SpaceAfter = 2
    $t.AutoFitBehavior(1)
    $t.AutoFitBehavior(2)
    $t.Borders.Enable = 0
    $t.Borders.Item(-1).LineStyle = 1
    $t.Borders.Item(-3).LineStyle = 1
    $t.Rows.Item(1).Borders.Item(-3).LineStyle = 1
    $t.Rows.Item(1).Range.Font.Bold = $true
    $t.Rows.Item(1).HeadingFormat = -1
  }
  foreach ($p in $doc.Paragraphs) { if ($p.Style.NameLocal -eq 'Source') { $p.Range.Font.Size = 9 } }
  foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
  $doc.Repaginate()
  $start = $null; $end = $null
  foreach ($p in $doc.Paragraphs) {
    if ($p.OutlineLevel -ne 1) { continue }
    $text = $p.Range.Text.Trim()
    if ($null -eq $start -and $text -match '^1\.\s') { $start = $p.Range.Start }
    if ($text -eq 'References') { $end = $p.Range.Start; break }
  }
  $total = $doc.ComputeStatistics(2)
  $counts = "Document: $total pages."
  if ($null -ne $start -and $null -ne $end) {
    $body = $doc.Range($start, $end)
    $words = $body.ComputeStatistics(0)
    $p0 = $doc.Range($start, $start).Information(3)
    $p1 = $doc.Range($end - 1, $end - 1).Information(3)
    $counts = "Body (Sections 1-6, figures and tables included): $($p1 - $p0 + 1) pages, $words words. Whole document: $total pages."
  }
  $rng = $doc.Content
  if ($rng.Find.Execute('{{COUNTS}}')) { $rng.Text = $counts }
  foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
  $doc.Save()
  if ($Pdf) { $doc.ExportAsFixedFormat($Pdf, 17) }
  $doc.Close()
  Write-Output $counts
} finally { $word.Quit() }
"""


def word_available() -> bool:
    probe = ["powershell", "-NoProfile", "-Command",
             "if (Test-Path 'Registry::HKEY_CLASSES_ROOT\\Word.Application') { exit 0 } else { exit 1 }"]
    return shutil.which("powershell") is not None and subprocess.run(probe).returncode == 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pdf", action="store_true", help="also export a PDF (needs Microsoft Word)")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    ref, docx, pdf = OUT / "reference.docx", OUT / f"{NAME}.docx", OUT / f"{NAME}.pdf"
    reference_docx(ref)
    today = dt.date.today()
    if docx.exists():  # Word holds a lock that os.access does not see
        try:
            open(docx, "r+b").close()
        except PermissionError:
            raise SystemExit(f"{docx.name} is open in Word. Close it and run the build again.") from None
    pypandoc.convert_text(
        source_text(), "docx", format="markdown", outputfile=str(docx),
        extra_args=["--citeproc", f"--bibliography={HERE / 'references.bib'}", f"--csl={HERE / 'apa.csl'}",
                    f"--reference-doc={ref}", f"--resource-path={HERE}",
                    f"--metadata=date:Draft, {today.day} {today:%B %Y}"])
    print(docx)
    if word_available():
        ps1 = OUT / "word_post.ps1"
        ps1.write_text(WORD_SCRIPT, encoding="utf-8")
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1),
                        "-Docx", str(docx), "-Pdf", str(pdf) if args.pdf else ""], check=True)
    else:
        print("Microsoft Word not found: open the document and update the index (F9); {{COUNTS}} stays unfilled.")


if __name__ == "__main__":
    main()
