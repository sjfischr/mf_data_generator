"""Document Assembler Lambda — combines sections into final DOCX package."""

import io
import json
import logging
import os
import subprocess
import tempfile
import zipfile

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
    """Convert markdown to DOCX using pandoc."""
    with tempfile.TemporaryDirectory() as tmpdir:
        md_path = os.path.join(tmpdir, "report.md")
        docx_path = os.path.join(tmpdir, "report.docx")

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown)

        # Download images to temp dir for pandoc
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
        except Exception as e:
            logger.warning("Could not download images: %s", e)

        # Run pandoc
        cmd = [
            "pandoc", md_path,
            "-o", docx_path,
            "--from", "markdown",
            "--to", "docx",
            "--toc",
            "--toc-depth=3",
            f"--resource-path={tmpdir}",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.error("Pandoc failed: %s", result.stderr)
            raise RuntimeError(f"Pandoc conversion failed: {result.stderr}")

        with open(docx_path, "rb") as f:
            return f.read()


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
