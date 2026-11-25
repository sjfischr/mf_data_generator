"""Shared DOCX rendering helpers for appraisal and lender-narrative documents."""

from __future__ import annotations

import io
import os
import re
import tempfile

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt


SYNTHETIC_FOOTER = "Synthetic document — not for lending or valuation use"


def add_footer(doc: Document, text: str) -> None:
    for section in doc.sections:
        footer = section.footer
        paragraph = footer.paragraphs[0]
        paragraph.text = text
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in paragraph.runs:
            run.font.size = Pt(8)
            run.italic = True


def add_cover_page(
    doc: Document,
    property_name: str,
    lender_name: str,
    title: str,
    location_text: str = "",
    cover_image_path: str | None = None,
):
    lender = doc.add_paragraph()
    lender.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = lender.add_run(lender_name)
    run.bold = True
    run.font.size = Pt(22)

    title_paragraph = doc.add_paragraph()
    title_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_paragraph.add_run(title)
    title_run.bold = True
    title_run.font.size = Pt(16)

    doc.add_paragraph()

    name = doc.add_paragraph()
    name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    name_run = name.add_run(property_name)
    name_run.bold = True
    name_run.font.size = Pt(28)

    if location_text:
        location = doc.add_paragraph()
        location.alignment = WD_ALIGN_PARAGRAPH.CENTER
        location.add_run(location_text)

    if cover_image_path:
        try:
            doc.add_picture(cover_image_path, width=Inches(6.2))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        except Exception:
            pass

    synthetic = doc.add_paragraph()
    synthetic.alignment = WD_ALIGN_PARAGRAPH.CENTER
    synthetic_run = synthetic.add_run(
        "Synthetic document — not for lending or valuation use"
    )
    synthetic_run.italic = True
    synthetic_run.font.size = Pt(10)
    doc.add_page_break()


def is_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 3


def is_separator(line: str) -> bool:
    if not is_table_line(line):
        return False
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return all(cell and re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def add_formatted_text(paragraph, text: str) -> None:
    pattern = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|[^*]+)")
    for part in pattern.findall(text):
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        elif part.startswith("*") and part.endswith("*"):
            run = paragraph.add_run(part[1:-1])
            run.italic = True
        else:
            paragraph.add_run(part)


def render_markdown_table(doc: Document, table_lines: list[str]) -> bool:
    rows = [
        table_row(line)
        for line in table_lines
        if not is_separator(line)
    ]
    if len(rows) < 2:
        return False
    col_count = max(len(row) for row in rows)
    table = doc.add_table(rows=len(rows), cols=col_count)
    table.style = "Table Grid"
    for row_index, row in enumerate(rows):
        for col_index in range(col_count):
            cell_text = row[col_index] if col_index < len(row) else ""
            paragraph = table.cell(row_index, col_index).paragraphs[0]
            paragraph.clear()
            add_formatted_text(paragraph, cell_text)
            if row_index == 0:
                for run in paragraph.runs:
                    run.bold = True
    return True


def markdown_to_docx(
    markdown: str,
    *,
    property_name: str = "Subject Property",
    lender_name: str = "NorthBridge Multifamily Capital",
    title: str = "Synthetic Multifamily Document",
    location_text: str = "",
    cover_image_path: str | None = None,
    footer_text: str = SYNTHETIC_FOOTER,
    image_map: dict[str, str] | None = None,
) -> bytes:
    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    add_cover_page(
        doc,
        property_name,
        lender_name,
        title,
        location_text,
        cover_image_path,
    )
    add_footer(doc, footer_text)

    image_map = image_map or {}
    lines = markdown.split("\n")
    i = 0
    in_list = False
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if is_table_line(line):
            table_lines = []
            while i < len(lines) and is_table_line(lines[i]):
                table_lines.append(lines[i])
                i += 1
            render_markdown_table(doc, table_lines)
            in_list = False
            continue

        if stripped == r"\newpage":
            doc.add_page_break()
            i += 1
            continue

        if line.startswith("# "):
            doc.add_heading(line[2:].strip(), level=1)
        elif line.startswith("## "):
            doc.add_heading(line[3:].strip(), level=2)
        elif line.startswith("### "):
            doc.add_heading(line[4:].strip(), level=3)
        elif re.match(r"^!\[([^\]]*)\]\(([^\)]+)\)", stripped):
            match = re.match(r"^!\[([^\]]*)\]\(([^\)]+)\)", stripped)
            alt_text = match.group(1)
            image_path = image_map.get(os.path.basename(match.group(2)))
            if image_path:
                try:
                    doc.add_picture(image_path, width=Inches(5))
                    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                except Exception:
                    doc.add_paragraph(f"[Image: {alt_text}]")
            else:
                doc.add_paragraph(f"[Image: {alt_text}]")
        elif stripped.startswith("- ") or stripped.startswith("* "):
            paragraph = doc.add_paragraph(style="List Bullet")
            add_formatted_text(paragraph, stripped[2:].strip())
            in_list = True
        else:
            number_match = re.match(r"^\s*\d+\.\s+(.+)$", line)
            if number_match:
                paragraph = doc.add_paragraph(style="List Number")
                add_formatted_text(paragraph, number_match.group(1).strip())
                in_list = True
            elif stripped:
                in_list = False
                paragraph = doc.add_paragraph()
                add_formatted_text(paragraph, stripped)
        i += 1

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
