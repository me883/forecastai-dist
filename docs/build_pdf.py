"""
build_pdf.py
~~~~~~~~~~~~
Converts CFO_TUTORIAL.md -> CFO_TUTORIAL.pdf using ReportLab (pure-Python).

Usage:
    python docs/build_pdf.py
"""

from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable, KeepTogether, PageBreak, Paragraph,
    SimpleDocTemplate, Spacer, Table, TableStyle,
)
from reportlab.platypus.flowables import Flowable

HERE    = Path(__file__).parent
SRC_MD  = HERE / "CFO_TUTORIAL.md"
OUT_PDF = HERE / "CFO_TUTORIAL.pdf"

# Palette
BLUE_DARK  = colors.HexColor("#1d4ed8")
BLUE_MED   = colors.HexColor("#3b82f6")
BLUE_LIGHT = colors.HexColor("#dbeafe")
SLATE_900  = colors.HexColor("#0f172a")
SLATE_700  = colors.HexColor("#334155")
SLATE_500  = colors.HexColor("#64748b")
SLATE_200  = colors.HexColor("#e2e8f0")
SLATE_50   = colors.HexColor("#f8fafc")
CODE_BG    = colors.HexColor("#0f172a")
CODE_FG    = colors.HexColor("#e2e8f0")
VIOLET     = colors.HexColor("#7c3aed")
GREEN_DK   = colors.HexColor("#16a34a")

BODY_FONT = "Helvetica"
BOLD_FONT = "Helvetica-Bold"
MONO_FONT = "Courier"

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm


def S(name, **kw):
    return ParagraphStyle(name, **kw)


STYLES = {
    "cover_title": S("cover_title", fontName=BOLD_FONT, fontSize=26, leading=32,
        textColor=SLATE_900, spaceAfter=6),
    "cover_sub": S("cover_sub", fontName=BODY_FONT, fontSize=12, leading=17,
        textColor=SLATE_500, spaceAfter=20),
    "h1": S("h1", fontName=BOLD_FONT, fontSize=17, leading=22,
        textColor=SLATE_900, spaceBefore=14, spaceAfter=5),
    "h2": S("h2", fontName=BOLD_FONT, fontSize=12, leading=16,
        textColor=BLUE_DARK, spaceBefore=12, spaceAfter=4),
    "h3": S("h3", fontName=BOLD_FONT, fontSize=10, leading=14,
        textColor=SLATE_700, spaceBefore=9, spaceAfter=3),
    "body": S("body", fontName=BODY_FONT, fontSize=9.5, leading=14.5,
        textColor=SLATE_700, spaceAfter=6),
    "bullet": S("bullet", fontName=BODY_FONT, fontSize=9.5, leading=14,
        textColor=SLATE_700, spaceAfter=2, leftIndent=14),
    "blockquote": S("blockquote", fontName=BODY_FONT, fontSize=9.5, leading=14.5,
        textColor=colors.HexColor("#0c4a6e"), leftIndent=14, spaceAfter=6, spaceBefore=4),
    "code_caption": S("code_caption", fontName=BOLD_FONT, fontSize=7.5, leading=11,
        textColor=SLATE_500, spaceAfter=2),
    "footer": S("footer", fontName=BODY_FONT, fontSize=7.5, leading=10,
        textColor=SLATE_500),
}


def _on_page(canvas, doc):
    if doc.page == 1:
        return
    canvas.saveState()
    canvas.setStrokeColor(SLATE_200)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, PAGE_H - 12*mm, PAGE_W - MARGIN, PAGE_H - 12*mm)
    canvas.setFont(BODY_FONT, 7.5)
    canvas.setFillColor(SLATE_500)
    canvas.drawString(MARGIN, PAGE_H - 10*mm, "ForecastAI + Claude Desktop -- CFO Tutorial")
    canvas.line(MARGIN, 12*mm, PAGE_W - MARGIN, 12*mm)
    canvas.drawString(MARGIN, 8*mm, "March 2026  |  Confidential")
    canvas.drawRightString(PAGE_W - MARGIN, 8*mm, f"Page {doc.page}")
    canvas.restoreState()


class CodeBlock(Flowable):
    def __init__(self, text, bg=CODE_BG, fg=CODE_FG):
        super().__init__()
        self.text   = text
        self.bg     = bg
        self.fg     = fg
        self._lines = text.split("\n")

    def wrap(self, avail_w, avail_h):
        self.width  = avail_w
        self.height = len(self._lines) * 11 + 16
        return self.width, self.height

    def draw(self):
        line_h, pad = 11, 8
        h = len(self._lines) * line_h + 2 * pad
        self.canv.setFillColor(self.bg)
        self.canv.roundRect(0, -h, self.width, h, 5, fill=1, stroke=0)
        self.canv.setFont(MONO_FONT, 7.5)
        self.canv.setFillColor(self.fg)
        y = -pad - line_h
        for ln in self._lines:
            self.canv.drawString(pad + 2, y, ln[:120])  # truncate very long lines
            y -= line_h


class BQBox(Flowable):
    def __init__(self, text, bar=BLUE_MED, bg=BLUE_LIGHT):
        super().__init__()
        self.text = text
        self.bar  = bar
        self.bg   = bg

    def wrap(self, avail_w, avail_h):
        self.width = avail_w
        inner_w    = avail_w - 20
        p = Paragraph(self.text, STYLES["blockquote"])
        _, h = p.wrapOn(None, inner_w, 9999)
        self.height = h + 16
        return self.width, self.height

    def draw(self):
        pad, h = 8, self.height
        self.canv.setFillColor(self.bg)
        self.canv.roundRect(0, -h, self.width, h, 4, fill=1, stroke=0)
        self.canv.setFillColor(self.bar)
        self.canv.rect(0, -h, 3, h, fill=1, stroke=0)
        inner_w = self.width - 20
        p = Paragraph(self.text, STYLES["blockquote"])
        p.wrapOn(self.canv, inner_w, 9999)
        p.drawOn(self.canv, 12, -(h - pad))


def _esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline(t):
    t = re.sub(r"`([^`]+)`",
               lambda m: f'<font face="Courier" color="#7c3aed" size="8">{_esc(m.group(1))}</font>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"\*([^*]+)\*",     r"<i>\1</i>", t)
    return t


def _make_table(header, rows):
    col_n = max(len(header), 1)
    avail = PAGE_W - 2 * MARGIN
    col_w = avail / col_n

    def cell(txt, bold=False):
        st = ParagraphStyle("tc", fontName=BOLD_FONT if bold else BODY_FONT,
            fontSize=8.5, leading=12,
            textColor=colors.white if bold else SLATE_700)
        return Paragraph(_inline(_esc(str(txt))), st)

    data = [[cell(h, True) for h in header]]
    for row in rows:
        # Pad/truncate row to match header length
        r = list(row) + [""] * col_n
        data.append([cell(r[c]) for c in range(col_n)])

    tbl = Table(data, colWidths=[col_w] * col_n, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  BLUE_DARK),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, SLATE_50]),
        ("GRID",          (0, 0), (-1, -1), 0.3, SLATE_200),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    return tbl


def parse_md(md_text):
    story   = []
    lines   = md_text.split("\n")
    i       = 0
    first_h1 = True

    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        # HR
        if re.match(r"^-{3,}$", line.strip()):
            story.append(HRFlowable(width="100%", thickness=0.5, color=SLATE_200,
                                    spaceBefore=4, spaceAfter=4))
            i += 1
            continue

        # Fenced code
        if line.startswith("```"):
            lang = line[3:].strip()
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1
            text = "\n".join(code_lines)
            if lang == "mermaid":
                story.append(Paragraph(
                    '<font color="#57534e"><b>Dependency Diagram (rendered in Claude Desktop)</b></font>',
                    STYLES["code_caption"]))
                story.append(CodeBlock(text, bg=colors.HexColor("#fafaf9"),
                                       fg=colors.HexColor("#44403c")))
            else:
                story.append(CodeBlock(text))
            story.append(Spacer(1, 4))
            continue

        # Headings
        m = re.match(r"^(#{1,4})\s+(.*)", line)
        if m:
            level = len(m.group(1))
            text  = _inline(_esc(m.group(2).strip()))
            if level == 1:
                if first_h1:
                    story.append(Paragraph(text, STYLES["cover_title"]))
                    first_h1 = False
                else:
                    story.append(PageBreak())
                    story.append(Paragraph(text, STYLES["h1"]))
                    story.append(HRFlowable(width="100%", thickness=1.5,
                                            color=BLUE_MED, spaceAfter=5))
            elif level == 2:
                story.append(Paragraph(text, STYLES["h2"]))
                story.append(HRFlowable(width="100%", thickness=0.5,
                                        color=BLUE_LIGHT, spaceAfter=3))
            elif level == 3:
                story.append(Paragraph(text, STYLES["h3"]))
            else:
                story.append(Paragraph(f"<b>{text}</b>", STYLES["body"]))
            i += 1
            continue

        # Blockquote
        if line.startswith(">"):
            bq = []
            while i < len(lines) and lines[i].startswith(">"):
                bq.append(lines[i].lstrip("> ").strip())
                i += 1
            story.append(Spacer(1, 2))
            story.append(BQBox(_inline(_esc(" ".join(bq)))))
            story.append(Spacer(1, 4))
            continue

        # Table
        if line.strip().startswith("|") and "|" in line:
            tbl_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                tbl_lines.append(lines[i])
                i += 1
            if len(tbl_lines) < 2:
                continue
            def split_row(r):
                return [c.strip() for c in r.strip().strip("|").split("|")]
            header = split_row(tbl_lines[0])
            rows   = [split_row(r) for r in tbl_lines[2:] if r.strip()]
            story.append(Spacer(1, 4))
            story.append(_make_table(header, rows))
            story.append(Spacer(1, 6))
            continue

        # Bullet / numbered list
        if re.match(r"^[-*\d]", line) and (line[1:2] in (" ", ".") or
                                             re.match(r"^\d+\.\s", line)):
            items = []
            while i < len(lines):
                ln = lines[i]
                m2 = re.match(r"^[-*]\s+(.*)", ln)
                m3 = re.match(r"^\d+\.\s+(.*)", ln)
                m4 = re.match(r"^-\s+\[[ x]\]\s+(.*)", ln)
                if m4:
                    done = ln[3] == "x"
                    items.append(("check", done, m4.group(1).strip()))
                    i += 1
                elif m2:
                    items.append(("bullet", False, m2.group(1).strip()))
                    i += 1
                elif m3:
                    items.append(("num", False, m3.group(1).strip()))
                    i += 1
                else:
                    break
            for kind, done, txt in items:
                if kind == "check":
                    mark = "[x]" if done else "[ ]"
                else:
                    mark = "•"
                story.append(Paragraph(f"{mark}  {_inline(_esc(txt))}", STYLES["bullet"]))
            story.append(Spacer(1, 4))
            continue

        # Plain paragraph
        para_lines = []
        while i < len(lines):
            ln = lines[i]
            if (not ln.strip() or ln.startswith("#") or ln.startswith(">")
                    or ln.startswith("```") or ln.strip().startswith("|")
                    or re.match(r"^-{3,}$", ln.strip())
                    or re.match(r"^[-*]\s", ln) or re.match(r"^\d+\.\s", ln)):
                break
            para_lines.append(ln)
            i += 1
        text = " ".join(para_lines).strip()
        if text:
            story.append(Paragraph(_inline(_esc(text)), STYLES["body"]))

    return story


def build():
    print(f"Reading {SRC_MD.name} ...")
    md_text = SRC_MD.read_text()

    print("Parsing Markdown ...")
    story = parse_md(md_text)

    print(f"Rendering PDF -> {OUT_PDF.name} ...")
    doc = SimpleDocTemplate(
        str(OUT_PDF),
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=16*mm,   bottomMargin=18*mm,
        title="ForecastAI CFO Tutorial",
        author="ForecastAI",
        subject="Claude Desktop + Excel CFO Workflow Guide",
    )
    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    size_kb = OUT_PDF.stat().st_size / 1024
    print(f"Done!  {OUT_PDF}  ({size_kb:.0f} KB)")


if __name__ == "__main__":
    build()
