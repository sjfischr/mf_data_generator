"""Document Assembler Lambda — combines sections into final DOCX package."""

import io
import json
import logging
import os
import re
import tempfile
import zipfile

from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

from lambdas.shared import s3_utils
from lambdas.shared.models import CrosswalkData

logger = logging.getLogger(__name__)

SECTION_ORDER = [
    "section_01_introduction",
    "section_02_property_description",
    "section_03_market_analysis",
    "section_04_highest_best_use",
    "section_05_valuation_methodology",
    "section_06_sales_comparison",
    "section_07_income_approach",
    "section_08_cost_approach",
    "section_09_reconciliation",
    "section_10_assumptions",
    "section_11_certification",
    "section_12_addenda",
]


def collect_sections(job_id: str) -> str:
    """Read all section markdown files and combine in order."""
    combined = []

    for section_name in SECTION_ORDER:
        filename = f"sections/{section_name}.md"
        try:
            content = s3_utils.read_text(job_id, filename)
            combined.append(content)
            combined.append("\n\n\\newpage\n\n")
        except Exception as e:
            logger.warning("Section %s not found: %s", section_name, e)
            combined.append(f"\n\n*[Section {section_name} not available]*\n\n")

    return "\n".join(combined)


def insert_images(markdown: str, job_id: str) -> str:
    """Replace [IMAGE: description] placeholders with actual image references."""
    try:
        manifest = s3_utils.read_json(job_id, "images/manifest.json")
    except Exception:
        logger.warning("Image manifest not found, skipping image insertion")
        return markdown

    # Build lookup by description keywords
    image_lookup = {}
    for entry in manifest:
        if entry.get("status") == "success":
            desc_lower = entry.get("description", "").lower()
            image_lookup[entry["filename"]] = entry

    # Simple replacement: replace [IMAGE: ...] with markdown image syntax
    import re

    def replace_image(match):
        desc = match.group(1).strip()
        # Try to find a matching image
        for filename, entry in image_lookup.items():
            if any(word in entry.get("description", "").lower() for word in desc.lower().split()):
                return f"![{desc}](images/{filename})"
        return f"*[Photo: {desc}]*"

    return re.sub(r"\[IMAGE:\s*([^\]]+)\]", replace_image, markdown)


def markdown_to_docx(markdown: str, job_id: str) -> bytes:
    """Convert markdown to DOCX using python-docx."""
    doc = Document()
    
    # Set document margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
    
    # Download images to temp dir if needed
    image_files = {}
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            manifest = s3_utils.read_json(job_id, "images/manifest.json")
            img_dir = os.path.join(tmpdir, "images")
            os.makedirs(img_dir, exist_ok=True)
            
            s3 = s3_utils.get_s3_client()
            for entry in manifest:
                if entry.get("status") == "success":
                    s3_key = entry["s3_key"]
                    local_path = os.path.join(img_dir, entry["filename"])
                    s3.download_file(s3_utils.BUCKET, s3_key, local_path)
                    image_files[entry["filename"]] = local_path
        except Exception as e:
            logger.warning("Could not download images: %s", e)
        
        # Parse markdown line by line
        lines = markdown.split('\n')
        i = 0
        in_list = False
        
        while i < len(lines):
            line = lines[i]
            
            # Page break
            if line.strip() == '\\newpage':
                doc.add_page_break()
                i += 1
                continue
            
            # Heading 1
            if line.startswith('# '):
                text = line[2:].strip()
                doc.add_heading(text, level=1)
                i += 1
                continue
            
            # Heading 2
            if line.startswith('## '):
                text = line[3:].strip()
                doc.add_heading(text, level=2)
                i += 1
                continue
            
            # Heading 3
            if line.startswith('### '):
                text = line[4:].strip()
                doc.add_heading(text, level=3)
                i += 1
                continue
            
            # Image reference
            img_match = re.match(r'!\[([^\]]*)\]\(([^\)]+)\)', line.strip())
            if img_match:
                alt_text = img_match.group(1)
                img_path = img_match.group(2)
                filename = os.path.basename(img_path)
                
                if filename in image_files:
                    try:
                        doc.add_picture(image_files[filename], width=Inches(5))
                        last_paragraph = doc.paragraphs[-1]
                        last_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        if alt_text:
                            caption = doc.add_paragraph(alt_text)
                            caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            caption.runs[0].font.size = Pt(10)
                            caption.runs[0].font.italic = True
                    except Exception as e:
                        logger.warning("Could not insert image %s: %s", filename, e)
                        doc.add_paragraph(f"[Image: {alt_text}]")
                else:
                    doc.add_paragraph(f"[Image: {alt_text}]")
                i += 1
                continue
            
            # Bullet list item
            if line.strip().startswith('- ') or line.strip().startswith('* '):
                text = line.strip()[2:].strip()
                text = apply_inline_formatting(text)
                p = doc.add_paragraph(style='List Bullet')
                add_formatted_text(p, text)
                in_list = True
                i += 1
                continue
            
            # Numbered list item
            num_match = re.match(r'^\s*\d+\.\s+(.+)$', line)
            if num_match:
                text = num_match.group(1).strip()
                text = apply_inline_formatting(text)
                p = doc.add_paragraph(style='List Number')
                add_formatted_text(p, text)
                in_list = True
                i += 1
                continue
            
            # Empty line
            if not line.strip():
                if in_list:
                    in_list = False
                i += 1
                continue
            
            # Regular paragraph
            if line.strip():
                in_list = False
                text = apply_inline_formatting(line.strip())
                p = doc.add_paragraph()
                add_formatted_text(p, text)
            
            i += 1
    
    # Save to bytes
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


def apply_inline_formatting(text: str) -> str:
    """Preserve formatting markersto process later."""
    return text


def add_formatted_text(paragraph, text: str):
    """Add text with inline formatting (bold, italic) to a paragraph."""
    # Simple regex-based parser for **bold** and *italic*
    pattern = re.compile(r'(\*\*[^*]+\*\*|\*[^*]+\*|[^*]+)')
    parts = pattern.findall(text)
    
    for part in parts:
        if part.startswith('**') and part.endswith('**'):
            # Bold
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        elif part.startswith('*') and part.endswith('*'):
            # Italic  
            run = paragraph.add_run(part[1:-1])
            run.italic = True
        else:
            paragraph.add_run(part)


def create_zip_package(job_id: str, docx_bytes: bytes) -> bytes:
    """Create a ZIP file containing all deliverables."""
    buf = io.BytesIO()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add appraisal report
        zf.writestr("appraisal_report.docx", docx_bytes)

        # Add Excel files
        s3 = s3_utils.get_s3_client()
        excel_files = [
            "outputs/rent_roll.xlsx",
            "outputs/t12_year1.xlsx",
            "outputs/t12_year2.xlsx",
            "outputs/t12_year3.xlsx",
        ]
        for excel_file in excel_files:
            try:
                key = s3_utils.job_key(job_id, excel_file)
                obj = s3.get_object(Bucket=s3_utils.BUCKET, Key=key)
                filename = excel_file.split("/")[-1]
                zf.writestr(filename, obj["Body"].read())
            except Exception as e:
                logger.warning("Could not add %s to ZIP: %s", excel_file, e)

    return buf.getvalue()


def handler(event, context):
    job_id = event["job_id"]
    logger.info("Assembling final documents for job %s", job_id)

    # Collect and combine sections
    combined_markdown = collect_sections(job_id)

    # Insert images
    combined_markdown = insert_images(combined_markdown, job_id)

    # Convert to DOCX
    docx_bytes = markdown_to_docx(combined_markdown, job_id)

    # Upload DOCX
    s3_utils.write_bytes(
        job_id, "outputs/appraisal_report.docx", docx_bytes,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    # Create ZIP package
    zip_bytes = create_zip_package(job_id, docx_bytes)
    s3_utils.write_bytes(
        job_id, "outputs/loan_package.zip", zip_bytes,
        "application/zip",
    )

    # Generate presigned URLs (7 days)
    urls = {
        "appraisal": s3_utils.generate_presigned_url(job_id, "outputs/appraisal_report.docx"),
        "rent_roll": s3_utils.generate_presigned_url(job_id, "outputs/rent_roll.xlsx"),
        "t12_files": [
            s3_utils.generate_presigned_url(job_id, "outputs/t12_year1.xlsx"),
            s3_utils.generate_presigned_url(job_id, "outputs/t12_year2.xlsx"),
            s3_utils.generate_presigned_url(job_id, "outputs/t12_year3.xlsx"),
        ],
        "complete_package": s3_utils.generate_presigned_url(job_id, "outputs/loan_package.zip"),
    }

    # Save URLs to S3 for the download endpoint
    s3_utils.write_json(job_id, "outputs/download_urls.json", urls)

    logger.info("Assembly complete for job %s", job_id)

    return {
        "status": "success",
        "job_id": job_id,
        "outputs": urls,
    }
