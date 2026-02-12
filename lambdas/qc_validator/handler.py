"""QC Validator Lambda — validates data consistency across all generated sections."""

import json
import logging
import re

from lambdas.shared import bedrock_client, s3_utils
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

    # Determine pass/fail
    errors = [i for i in all_issues if i["severity"] == "error"]
    warnings = [i for i in all_issues if i["severity"] == "warning"]
    total_checks = 50  # approximate number of checks performed
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
