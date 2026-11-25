"""QC Validator Lambda — validates data consistency across all generated sections."""

import json
import logging
import re
import io

from openpyxl import load_workbook
from docx import Document

from lambdas.shared import s3_utils
from lambdas.shared.models import CrosswalkData

logger = logging.getLogger(__name__)


def check_numeric_in_text(text: str, value: int, label: str) -> dict | None:
    """Check if a numeric value appears in the text (with or without formatting)."""
    formatted = f"{value:,}"
    plain = str(value)
    if formatted not in text and plain not in text:
        return {
            "severity": "warning",
            "category": "missing_value",
            "description": f"{label} (${formatted}) not found in section text",
        }
    return None


def run_structural_checks(crosswalk: CrosswalkData) -> list[dict]:
    """Run Pydantic-level and calculated validation checks."""
    issues = []

    # Cap rate validation
    if not crosswalk.validate_cap_rate():
        noi = crosswalk.valuation.income_approach.stabilized_noi
        value = crosswalk.valuation.income_approach.indicated_value
        expected = round((noi / value) * 100, 2)
        actual = crosswalk.valuation.income_approach.cap_rate
        issues.append({
            "severity": "error",
            "category": "cap_rate_mismatch",
            "description": f"Cap rate {actual}% != NOI/Value ({expected}%)",
            "location": "crosswalk-data.json",
        })

    # Value per unit validation
    if not crosswalk.validate_value_per_unit():
        issues.append({
            "severity": "error",
            "category": "value_per_unit_mismatch",
            "description": "Value per unit doesn't match market_value / total_units",
            "location": "crosswalk-data.json",
        })

    # Occupancy units validation
    if not crosswalk.validate_occupancy_units():
        issues.append({
            "severity": "error",
            "category": "occupancy_unit_mismatch",
            "description": "Occupied + vacant units != total units",
            "location": "crosswalk-data.json",
        })

    # Unit mix SF totals
    total_sf_from_mix = sum(u.total_sf for u in crosswalk.property_physical.unit_mix)
    gba = crosswalk.property_physical.gross_building_area_sf
    if total_sf_from_mix > gba:
        issues.append({
            "severity": "warning",
            "category": "sf_mismatch",
            "description": (
                f"Unit mix total SF ({total_sf_from_mix:,}) exceeds "
                f"gross building area ({gba:,})"
            ),
            "location": "crosswalk-data.json",
        })

    return issues


def run_section_content_checks(crosswalk: CrosswalkData, job_id: str) -> list[dict]:
    """Check that key values appear in the generated section content."""
    issues = []
    prop = crosswalk.property_identification
    val = crosswalk.valuation
    fin = crosswalk.financial_data

    section_files = s3_utils.list_files(job_id, "sections/")

    for s3_key in section_files:
        if not s3_key.endswith(".md"):
            continue

        filename = s3_key.split("/")[-1]
        try:
            # Read via raw key
            content = s3_utils.get_s3_client().get_object(
                Bucket=s3_utils.BUCKET, Key=s3_key
            )["Body"].read().decode("utf-8")
        except Exception as e:
            issues.append({
                "severity": "error",
                "category": "missing_section",
                "description": f"Cannot read section file: {filename} — {e}",
                "location": filename,
            })
            continue

        # Check property name appears in all sections
        if prop.property_name not in content:
            issues.append({
                "severity": "warning",
                "category": "missing_property_name",
                "description": f"Property name '{prop.property_name}' not found",
                "location": filename,
            })

        # Section-specific checks
        if "section_07" in filename:
            checks = [
                (fin.net_operating_income, "NOI"),
                (fin.pro_forma_income.effective_gross_income, "EGI"),
                (fin.pro_forma_income.potential_gross_income, "PGI"),
            ]
            for value, label in checks:
                issue = check_numeric_in_text(content, value, label)
                if issue:
                    issue["location"] = filename
                    issues.append(issue)

        if "section_09" in filename:
            issue = check_numeric_in_text(
                content,
                val.final_value_conclusion.market_value,
                "Final Market Value",
            )
            if issue:
                issue["severity"] = "error"
                issue["location"] = filename
                issues.append(issue)

    return issues


NARRATIVE_HEADINGS = [
    "1. Loan Summary & Salient Facts",
    "2. Executive Summary & Recommendation",
    "3. Sources & Uses",
    "4. Borrower, Key Principals & Guarantor",
    "5. Property Management",
    "6. Property Description",
    "7. Market & Submarket Analysis",
    "8. Rent Roll & Occupancy Analysis",
    "9. Historical Operating Performance vs. Underwriting",
    "10. Underwritten NCF & Loan Sizing",
    "11. Appraisal Review",
    "12. Third-Party Reports",
    "13. Refinance Risk Analysis",
    "14. Strengths, Risks & Mitigants",
    "15. Waivers & Exceptions",
    "16. Conditions of Approval",
    "17. Underwriter Conclusion & Approval",
]


class CheckLog:
    """Collects issues and counts every individual check performed."""

    def __init__(self):
        self.count = 0
        self.issues: list[dict] = []

    def check(self, passed: bool, severity: str, category: str, description: str, location: str) -> None:
        self.count += 1
        if not passed:
            self.issues.append({
                "severity": severity,
                "category": category,
                "description": description,
                "location": location,
            })


def _read_object(job_id: str, path: str) -> bytes:
    s3 = s3_utils.get_s3_client()
    return s3.get_object(Bucket=s3_utils.BUCKET, Key=s3_utils.job_key(job_id, path))["Body"].read()


def check_financing(crosswalk: CrosswalkData, log: CheckLog) -> None:
    financing = crosswalk.financing
    if financing is None:
        return
    log.check(financing.underwritten_dscr + 1e-9 >= financing.tier_minimum_dscr, "error", "tier_dscr",
              f"Underwritten DSCR {financing.underwritten_dscr:.2f}x below tier minimum "
              f"{financing.tier_minimum_dscr:.2f}x", "crosswalk-data.json")
    log.check(financing.ltv_underwriting_value <= financing.tier_maximum_ltv + 1e-9, "error", "tier_ltv",
              f"LTV {financing.ltv_underwriting_value:.2f}% above tier maximum "
              f"{financing.tier_maximum_ltv:.2f}%", "crosswalk-data.json")


def narrative_text(doc) -> str:
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        parts.extend(cell.text for row in table.rows for cell in row.cells)
    return "\n".join(parts)


def check_narrative(crosswalk: CrosswalkData, job_id: str, log: CheckLog) -> None:
    location = "lender_narrative.docx"
    try:
        doc = Document(io.BytesIO(_read_object(job_id, "outputs/lender_narrative.docx")))
    except Exception as exc:
        log.check(False, "error", "missing_narrative", f"Cannot read lender narrative: {exc}", location)
        return
    log.check(True, "error", "missing_narrative", "", location)

    headings = [p.text.strip() for p in doc.paragraphs if p.style.name.startswith("Heading")]
    positions = []
    for heading in NARRATIVE_HEADINGS:
        present = heading in headings
        log.check(present, "error", "missing_narrative_heading", f"Narrative missing heading: {heading}", location)
        if present:
            positions.append(headings.index(heading))
    log.check(positions == sorted(positions), "error", "narrative_heading_order",
              "Narrative headings are out of order", location)

    financing = crosswalk.financing
    if financing is None or crosswalk.operating_history is None:
        return
    text = narrative_text(doc)
    figures = [
        ("error", f"${financing.loan_amount:,}", "loan amount"),
        ("warning", f"{financing.underwritten_dscr:.2f}x", "Underwritten DSCR"),
        ("warning", f"{financing.ltv_underwriting_value:.2f}%", "LTV"),
        ("warning", f"${crosswalk.operating_history.underwritten.ncf:,}", "Underwritten NCF"),
    ]
    for severity, formatted, label in figures:
        log.check(formatted in text, severity, "narrative_missing_figure",
                  f"Lender narrative missing {label} {formatted}", location)

    try:
        warnings = json.loads(_read_object(job_id, "sections/lender_narrative_warnings.json")).get("warnings", [])
    except Exception:
        warnings = []
    for warning in warnings:
        log.check(False, "warning", "narrative_number_guard", warning, location)


def check_t12_workbooks(crosswalk: CrosswalkData, job_id: str, log: CheckLog) -> None:
    if crosswalk.operating_history is None:
        return
    for year_number in (1, 2, 3):
        location = f"t12_year{year_number}.xlsx"
        try:
            wb = load_workbook(io.BytesIO(_read_object(job_id, f"outputs/{location}")), data_only=False)
            ws = wb.active
        except Exception as exc:
            log.check(False, "error", "missing_t12", f"Cannot read {location}: {exc}", location)
            continue
        log.check(True, "error", "missing_t12", "", location)

        totals = {"4": 0, "5": 0, "6": 0}
        detail_count = 0
        for row in range(5, ws.max_row + 1):
            label = str(ws.cell(row, 1).value or "")
            prefix = label[:1]
            if not (label[:4].isdigit() and prefix in totals):
                continue
            detail_count += 1
            totals[prefix] += sum(
                ws.cell(row, col).value for col in range(2, 14)
                if isinstance(ws.cell(row, col).value, (int, float))
            )
        expected = getattr(crosswalk.operating_history, f"year_{year_number}")
        egi, opex, reserves = totals["4"], totals["5"], totals["6"]
        comparisons = [
            ("EGI", egi, expected.effective_gross_income),
            ("Total Operating Expenses", opex, expected.total_operating_expenses),
            ("NOI", egi - opex, expected.noi),
            ("NCF", egi - opex - reserves, expected.ncf),
        ]
        for label, actual, target in comparisons:
            log.check(actual == target, "error", "t12_total_mismatch",
                      f"{location} {label} {actual:,} != crosswalk {target:,}", location)
        log.check(detail_count >= 40, "warning", "t12_detail",
                  f"{location} has only {detail_count} detail accounts", location)


def check_images(job_id: str, log: CheckLog) -> None:
    try:
        manifest = json.loads(_read_object(job_id, "images/manifest.json"))
    except Exception:
        log.check(False, "warning", "missing_images", "Image manifest not found", "images/manifest.json")
        return
    for entry in manifest:
        log.check(entry.get("status") == "success", "warning", "image_failed",
                  f"Image {entry.get('filename')} failed: {entry.get('reason') or entry.get('error')}",
                  "images/manifest.json")


def handler(event, context):
    job_id = event["job_id"]
    logger.info("Running QC validation for job %s", job_id)

    # Load crosswalk
    data = s3_utils.read_json(job_id, "crosswalk-data.json")
    crosswalk = CrosswalkData.model_validate(data)

    all_issues = []

    # Structural checks (4) and section content checks
    structural = run_structural_checks(crosswalk)
    all_issues.extend(structural)
    content_issues = run_section_content_checks(crosswalk, job_id)
    all_issues.extend(content_issues)
    section_count = len([k for k in s3_utils.list_files(job_id, "sections/") if k.endswith(".md")])
    legacy_checks = 4 + section_count + 4

    log = CheckLog()
    check_financing(crosswalk, log)
    check_narrative(crosswalk, job_id, log)
    check_t12_workbooks(crosswalk, job_id, log)
    check_images(job_id, log)
    all_issues.extend(log.issues)

    errors = [i for i in all_issues if i["severity"] == "error"]
    warnings = [i for i in all_issues if i["severity"] == "warning"]
    total_checks = legacy_checks + log.count
    checks_passed = total_checks - len(all_issues)

    status = "fail" if errors else "pass"

    report = {
        "status": status,
        "checks_performed": total_checks,
        "checks_passed": max(0, checks_passed),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "issues": all_issues,
    }

    s3_utils.write_json(job_id, "qc_report.json", report)

    logger.info("QC complete: %s (%d errors, %d warnings)", status, len(errors), len(warnings))

    return {
        "status": "success",
        "job_id": job_id,
        "qc_status": status.upper(),
        "qc_report_key": f"jobs/{job_id}/qc_report.json",
    }
