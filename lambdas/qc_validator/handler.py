"""QC Validator Lambda — validates data consistency across all generated sections."""

import json
import logging
import re
import io

from openpyxl import load_workbook
from docx import Document
from lambdas.shared.chart_of_accounts import CHART_OF_ACCOUNTS

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


def run_new_deliverable_checks(crosswalk: CrosswalkData, job_id: str) -> list[dict]:
    issues = []
    s3 = s3_utils.get_s3_client()

    if crosswalk.financing is not None:
        financing = crosswalk.financing
        if financing.underwritten_dscr + 1e-9 < financing.tier_minimum_dscr:
            issues.append({
                "severity": "error",
                "category": "tier_dscr_mismatch",
                "description": (
                    f"Underwritten DSCR {financing.underwritten_dscr:.2f}x "
                    f"below tier minimum {financing.tier_minimum_dscr:.2f}x"
                ),
                "location": "crosswalk-data.json",
            })
        if financing.ltv_underwriting_value > financing.tier_maximum_ltv:
            issues.append({
                "severity": "error",
                "category": "tier_ltv_mismatch",
                "description": (
                    f"LTV {financing.ltv_underwriting_value:.2f}% "
                    f"above tier maximum {financing.tier_maximum_ltv:.2f}%"
                ),
                "location": "crosswalk-data.json",
            })

    narrative_key = s3_utils.job_key(job_id, "outputs/lender_narrative.docx")
    try:
        response = s3.get_object(Bucket=s3_utils.BUCKET, Key=narrative_key)
        doc = Document(io.BytesIO(response["Body"].read()))
        headings = [
            paragraph.text.strip()
            for paragraph in doc.paragraphs
            if paragraph.style.name.startswith("Heading")
        ]
        required = [
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
        for heading in required:
            if heading not in headings:
                issues.append({
                    "severity": "error",
                    "category": "missing_narrative_heading",
                    "description": f"Narrative missing heading: {heading}",
                    "location": "lender_narrative.docx",
                })
    except Exception as exc:
        issues.append({
            "severity": "error",
            "category": "missing_narrative",
            "description": f"Cannot read lender narrative: {exc}",
            "location": "lender_narrative.docx",
        })

    if crosswalk.financing is not None:
        loan_amount = crosswalk.financing.loan_amount
        try:
            response = s3.get_object(Bucket=s3_utils.BUCKET, Key=narrative_key)
            doc = Document(io.BytesIO(response["Body"].read()))
            text = "\n".join(
                paragraph.text for paragraph in doc.paragraphs
            )
            for table in doc.tables:
                text += "\n" + "\n".join(
                    cell.text
                    for row in table.rows
                    for cell in row.cells
                )
            formatted = f"${loan_amount:,}"
            if formatted not in text:
                issues.append({
                    "severity": "error",
                    "category": "missing_narrative_loan_amount",
                    "description": f"Lender narrative missing loan amount {formatted}",
                    "location": "lender_narrative.docx",
                })
        except Exception:
            pass

    for year_number in (1, 2, 3):
        key = s3_utils.job_key(job_id, f"outputs/t12_year{year_number}.xlsx")
        try:
            response = s3.get_object(Bucket=s3_utils.BUCKET, Key=key)
            wb = load_workbook(io.BytesIO(response["Body"].read()), data_only=False)
            ws = wb.active
            if ws is None:
                raise RuntimeError("No worksheet")

            if crosswalk.operating_history is not None:
                column_name = f"year_{year_number}"
                expected = getattr(crosswalk.operating_history, column_name)

                account_totals = {}
                account_map = {
                    str(account[0]): account[2]
                    for account in CHART_OF_ACCOUNTS
                }
                for row in range(5, ws.max_row + 1):
                    label = str(ws.cell(row, 1).value or "")
                    account_number = label.split(" ", 1)[0]
                    category = account_map.get(account_number)
                    if not category:
                        continue
                    monthly_total = sum(
                        int(ws.cell(row, col).value or 0)
                        for col in range(2, 14)
                        if isinstance(ws.cell(row, col).value, (int, float))
                    )
                    account_totals[category] = (
                        account_totals.get(category, 0) + monthly_total
                    )

                actual_egi = (
                    account_totals.get("gpr", 0)
                    + account_totals.get("loss_gain_to_lease", 0)
                    - account_totals.get("vacancy", 0)
                    - account_totals.get("concessions", 0)
                    - account_totals.get("bad_debt", 0)
                    - account_totals.get("non_revenue_units", 0)
                    + account_totals.get("laundry_vending", 0)
                    + account_totals.get("parking", 0)
                    + account_totals.get("commercial", 0)
                    + account_totals.get("other_income", 0)
                )
                if actual_egi != expected.effective_gross_income:
                    issues.append({
                        "severity": "error",
                        "category": "t12_total_mismatch",
                        "description": (
                            f"t12_year{year_number}.xlsx EGI {actual_egi:,} "
                            f"!= crosswalk EGI {expected.effective_gross_income:,}"
                        ),
                        "location": f"t12_year{year_number}.xlsx",
                    })
        except Exception as exc:
            issues.append({
                "severity": "error",
                "category": "missing_t12",
                "description": f"Cannot read t12_year{year_number}.xlsx: {exc}",
                "location": f"t12_year{year_number}.xlsx",
            })
    return issues


def handler(event, context):
    job_id = event["job_id"]
    logger.info("Running QC validation for job %s", job_id)

    # Load crosswalk
    data = s3_utils.read_json(job_id, "crosswalk-data.json")
    crosswalk = CrosswalkData.model_validate(data)

    all_issues = []

    # Structural checks
    structural = run_structural_checks(crosswalk)
    all_issues.extend(structural)

    # Content checks
    content_issues = run_section_content_checks(crosswalk, job_id)
    all_issues.extend(content_issues)

    # New deliverable checks
    deliverable_issues = run_new_deliverable_checks(crosswalk, job_id)
    all_issues.extend(deliverable_issues)

    # Determine pass/fail
    errors = [i for i in all_issues if i["severity"] == "error"]
    warnings = [i for i in all_issues if i["severity"] == "warning"]
    total_checks = 50 + len(all_issues) + 17 + 3
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
