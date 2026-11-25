"""Lender Narrative / Transaction Approval Memo Lambda."""

from __future__ import annotations

import json
import logging
import re

from lambdas.shared import bedrock_client, s3_utils
from lambdas.shared.docx_renderer import markdown_to_docx
from lambdas.shared.models import CrosswalkData
from .facts import build_fact_sheet, fmt_dollar
from .tables import (
    appraisal_reconciliation_table,
    dscr_sensitivity_table,
    loan_summary_table,
    operating_comparison_table,
    refinance_risk_table,
    sizing_table,
    sources_and_uses_table,
)

logger = logging.getLogger(__name__)

HEADINGS = [
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


def extract_numbers(text: str) -> list[str]:
    patterns = [
        r"\$[\d,]+(?:\.\d+)?",
        r"\b\d+(?:\.\d+)?%",
        r"\b\d+(?:\.\d+)?x\b",
    ]
    matches = []
    for pattern in patterns:
        matches.extend(re.findall(pattern, text))
    return matches


def validate_numbers(text: str, fact_sheet: dict[str, str]) -> list[str]:
    allowed = set(fact_sheet.values())
    unknown = []
    for number in extract_numbers(text):
        normalized = number.replace(",", "").strip()
        if normalized not in {
            value.replace(",", "").strip()
            for value in allowed
        }:
            unknown.append(number)
    return list(dict.fromkeys(unknown))


def generate_group(group_name: str, prompt: str, fact_sheet: dict[str, str]) -> str:
    system_prompt = (
        "You are a multifamily lender underwriter writing a synthetic "
        "Transaction Approval Memo. Use only the supplied facts. Do not "
        "invent any loan amount, rent, NOI, DSCR, LTV, valuation, date, "
        "or third-party conclusion. Output professional Markdown prose."
    )
    full_prompt = (
        f"{prompt}\n\n"
        "Allowed facts:\n"
        + json.dumps(fact_sheet, indent=2)
        + "\n\nDo not introduce a numeric figure that is absent from Allowed facts."
    )

    text = bedrock_client.invoke_model(
        prompt=full_prompt,
        model="opus",
        system_prompt=system_prompt,
        max_tokens=6000,
        temperature=0.3,
    )
    unknown = validate_numbers(text, fact_sheet)
    if unknown:
        retry_prompt = (
            full_prompt
            + "\n\nYour prior prose included these unsupported figures: "
            + ", ".join(unknown)
            + ". Remove or replace them with Allowed facts."
        )
        text = bedrock_client.invoke_model(
            prompt=retry_prompt,
            model="opus",
            system_prompt=system_prompt,
            max_tokens=6000,
            temperature=0.2,
        )
    return text


def build_narrative(crosswalk: CrosswalkData) -> tuple[str, list[str]]:
    facts = build_fact_sheet(crosswalk)
    sections = [
        loan_summary_table(crosswalk),
        "## 2. Executive Summary & Recommendation\n\n"
        "## 4. Borrower, Key Principals & Guarantor\n\n",
        sources_and_uses_table(crosswalk),
        "## 5. Property Management\n\n",
        "## 6. Property Description\n\n",
        "## 7. Market & Submarket Analysis\n\n",
        "## 8. Rent Roll & Occupancy Analysis\n\n",
        operating_comparison_table(crosswalk),
        sizing_table(crosswalk),
        dscr_sensitivity_table(crosswalk),
        appraisal_reconciliation_table(crosswalk),
        "## 12. Third-Party Reports\n\n",
        refinance_risk_table(crosswalk),
        "## 14. Strengths, Risks & Mitigants\n\n",
        "## 15. Waivers & Exceptions\n\n",
        "## 16. Conditions of Approval\n\n",
        "## 17. Underwriter Conclusion & Approval\n\n",
    ]

    prompts = [
        ("2. Executive Summary & Recommendation", "Summarize the recommendation, loan structure, and principal risks."),
        ("4. Borrower, Key Principals & Guarantor", "Analyze borrower experience, net worth, liquidity, and guarantor support."),
        ("5. Property Management", "Analyze property management capacity and the adequacy of staffing."),
        ("6-8. Property, Market, and Rent Roll", "Discuss property description, market position, occupancy, rents, and market depth."),
        ("12. Third-Party Reports", "Summarize appraisal, PCA, ESA, seismic and zoning findings."),
        ("14-17. Risks, Waivers, Conditions, Conclusion", "List at least three strengths, at least three risks with mitigants, waivers, conditions, and the underwriter conclusion."),
    ]

    generated = {}
    warnings = []
    for group_name, prompt in prompts:
        text = generate_group(group_name, prompt, facts)
        unknown = validate_numbers(text, facts)
        if unknown:
            warnings.append(
                f"{group_name} contained unsupported figures after retry: "
                + ", ".join(unknown)
            )
        generated[group_name] = text

    narrative = "\n\n".join(sections)
    for heading_marker, text in generated.items():
        if heading_marker.startswith("2."):
            narrative = narrative.replace(
                "## 2. Executive Summary & Recommendation\n\n",
                "## 2. Executive Summary & Recommendation\n\n" + text + "\n\n",
            )
        elif heading_marker.startswith("4."):
            narrative = narrative.replace(
                "## 4. Borrower, Key Principals & Guarantor\n\n",
                "## 4. Borrower, Key Principals & Guarantor\n\n" + text + "\n\n",
            )
        elif heading_marker.startswith("5."):
            narrative = narrative.replace(
                "## 5. Property Management\n\n",
                "## 5. Property Management\n\n" + text + "\n\n",
            )
        elif heading_marker.startswith("6-8."):
            narrative = narrative.replace(
                "## 6. Property Description\n\n",
                "## 6. Property Description\n\n" + text + "\n\n",
            )
        elif heading_marker.startswith("12."):
            narrative = narrative.replace(
                "## 12. Third-Party Reports\n\n",
                "## 12. Third-Party Reports\n\n" + text + "\n\n",
            )
        elif heading_marker.startswith("14-17."):
            narrative = narrative.replace(
                "## 14. Strengths, Risks & Mitigants\n\n",
                "## 14. Strengths, Risks & Mitigants\n\n" + text + "\n\n",
            )

    return narrative, warnings


def handler(event, context):
    job_id = event["job_id"]
    data = s3_utils.read_json(job_id, "crosswalk-data.json")
    crosswalk = CrosswalkData.model_validate(data)

    narrative, warnings = build_narrative(crosswalk)
    prop = crosswalk.property_identification
    location = f"{prop.address}, {prop.city}, {prop.state}"

    docx_bytes = markdown_to_docx(
        narrative,
        property_name=prop.property_name,
        lender_name="NorthBridge Multifamily Capital",
        title="Lender Narrative — Transaction Approval Memo",
        location_text=location,
        footer_text="Synthetic document — not for lending or valuation use",
    )
    s3_utils.write_bytes(
        job_id,
        "outputs/lender_narrative.docx",
        docx_bytes,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    s3_utils.write_json(
        job_id,
        "sections/lender_narrative_warnings.json",
        {"warnings": warnings},
    )
    return {
        "status": "success",
        "job_id": job_id,
        "s3_key": f"jobs/{job_id}/outputs/lender_narrative.docx",
        "warnings": warnings,
    }
