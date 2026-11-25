"""Lender Narrative / Transaction Approval Memo Lambda.

Code renders every table and figure from the crosswalk; Opus writes only the
prose around them. Prose figures are checked against the allowed figures.
"""

from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor

from lambdas.shared import bedrock_client, s3_utils
from lambdas.shared.docx_renderer import markdown_to_docx
from lambdas.shared.errors import TransientError
from lambdas.shared.models import CrosswalkData

try:  # package import (tests) vs. flat Lambda bundle (/var/task)
    from lambdas.lender_narrative_generator import tables
    from lambdas.lender_narrative_generator.facts import build_fact_sheet
except ImportError:  # pragma: no cover - exercised only inside Lambda
    import tables  # type: ignore[no-redef]
    from facts import build_fact_sheet  # type: ignore[no-redef]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

LENDER_NAME = "NorthBridge Multifamily Capital"
TITLE = "Lender Narrative — Transaction Approval Memo"
DISCLAIMER = "SYNTHETIC DOCUMENT — generated test data, not for lending, underwriting, or valuation use"

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

# Prose groups: section numbers each Opus call writes, plus its instructions.
PROSE_GROUPS = [
    ([2], "Write the executive summary: transaction overview, key credit metrics, principal "
          "strengths and risks, and a clear recommendation to approve with conditions."),
    ([4, 5], "Section 4: analyze borrower structure, key principals' experience, net worth, "
             "liquidity, and guarantor support versus the loan. Section 5: assess the management "
             "company, fee, and on-site staffing adequacy."),
    ([6, 7, 8], "Section 6: describe the improvements, unit mix, amenities, and condition. "
                "Section 7: analyze the submarket, vacancy, rent growth, comparable properties, and "
                "market depth. Section 8: analyze occupancy, in-place versus market rents, and loss to lease."),
    ([9, 11, 12], "Section 9: explain each material variance between Year 1 and Underwritten "
                  "(listed in the facts) and the trend across the three historical years. Section 11: "
                  "reconcile the appraiser pro forma with the lender underwriting and comment on the "
                  "valuation. Section 12: summarize third-party report findings and their underwriting impact."),
    ([10, 13, 14], "Section 10: explain the sizing, binding constraint, and DSCR sensitivity. "
                   "Section 13: assess refinance risk at maturity using the projection. Section 14: list "
                   "at least three strengths, then at least three risks each immediately followed by its "
                   "mitigant, formatted as bullets 'Risk: ...' / 'Mitigant: ...'."),
    ([15, 16, 17], "Section 15: state waivers and exceptions (state 'None requested' if none apply). "
                   "Section 16: list conditions of approval (e.g., repair escrow, reserve funding, "
                   "insurance, delivery items). Section 17: underwriter conclusion and approval block "
                   "with signature lines for the Underwriter and the Chief Underwriter."),
]

SYSTEM_PROMPT = (
    "You are a senior Fannie Mae DUS multifamily underwriter writing a synthetic Transaction "
    "Approval Memo (Lender Narrative). Write formal, concise, analytical prose. Use ONLY the "
    "facts provided. Cite figures exactly as they appear in the facts (e.g. $13,899,000, 1.25x, "
    "63.42%) and never invent loan, income, expense, value, ratio, or percentage figures. All "
    "names are fictitious. Do not write numbered headings; you may use ### subheadings, bullets, "
    "and bold text."
)

NUMBER_PATTERN = re.compile(
    r"(?P<dollar>\$\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:million|M)\b)?)"
    r"|(?P<pct>\b\d+(?:\.\d+)?\s?%)"
    r"|(?P<ratio>\b\d+\.\d+\s?x\b)"
)


def _parse_number(token: str) -> tuple[str, float, int]:
    kind = "$" if token.startswith("$") else "%" if token.endswith("%") else "x"
    text = token.replace("$", "").replace(",", "").replace("%", "").replace("x", "").strip()
    multiplier = 1
    if "million" in text or text.endswith("M"):
        text = text.replace("million", "").replace("M", "").strip()
        multiplier = 1_000_000
    decimals = len(text.split(".")[1]) if "." in text else 0
    value = float(text) * multiplier
    if multiplier > 1:
        decimals = -6 + decimals
    return kind, value, decimals


def allowed_numbers(*texts: str) -> dict[str, list[float]]:
    allowed: dict[str, list[float]] = {"$": [], "%": [], "x": []}
    for text in texts:
        for match in NUMBER_PATTERN.finditer(text):
            kind, value, _ = _parse_number(match.group(0))
            allowed[kind].append(value)
    return allowed


def unsupported_figures(prose: str, allowed: dict[str, list[float]]) -> list[str]:
    """Figures in prose that don't round-match any allowed figure of the same kind."""
    bad = []
    for match in NUMBER_PATTERN.finditer(prose):
        token = match.group(0)
        kind, value, decimals = _parse_number(token)
        tolerance = 1.0 if kind == "$" and decimals == 0 else 0.0
        ok = any(
            abs(round(a, decimals) - value) <= tolerance + 1e-6 for a in allowed[kind]
        )
        if not ok:
            bad.append(token)
    return list(dict.fromkeys(bad))


def split_sections(text: str, numbers: list[int]) -> dict[int, str]:
    """Split model output on '@@SECTION n@@' markers."""
    parts = re.split(r"@@SECTION\s+(\d+)@@", text)
    out: dict[int, str] = {}
    for i in range(1, len(parts) - 1, 2):
        number = int(parts[i])
        if number in numbers:
            body = parts[i + 1].strip()
            body = re.sub(r"^#{1,2}\s+", "### ", body, flags=re.MULTILINE)
            out[number] = body
    return out


def _invoke(prompt: str, max_tokens: int = 4000) -> str:
    for attempt in range(3):
        try:
            return bedrock_client.invoke_model(
                prompt=prompt, model="opus", system_prompt=SYSTEM_PROMPT,
                max_tokens=max_tokens, temperature=0.4,
            )
        except TransientError:
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("unreachable")


def generate_group(numbers: list[int], instructions: str, facts_json: str,
                   allowed: dict[str, list[float]]) -> tuple[dict[int, str], list[str]]:
    headings = [HEADINGS[n - 1] for n in numbers]
    prompt = (
        f"{instructions}\n\nWrite these Transaction Approval Memo sections: {', '.join(headings)}.\n"
        "Begin each section with a marker line exactly like '@@SECTION 4@@' (using the section "
        "number) followed by its prose. 150-400 words per section.\n\n"
        f"FACTS (JSON):\n{facts_json}"
    )
    text = _invoke(prompt)
    bad = unsupported_figures(text, allowed)
    if bad:
        retry = (
            prompt + "\n\nYour previous draft cited figures that are not in the facts: "
            + ", ".join(bad) + ". Rewrite without them, citing only figures from the facts."
        )
        text = _invoke(retry)
        bad = unsupported_figures(text, allowed)
    sections = split_sections(text, numbers)
    warnings = [f"Sections {numbers}: unsupported figures after retry: {', '.join(bad)}"] if bad else []
    for n in numbers:
        if n not in sections:
            warnings.append(f"Section {n}: model output missing; placeholder used")
            sections[n] = "_Commentary unavailable for this section._"
    return sections, warnings


def code_sections(cw: CrosswalkData) -> dict[int, str]:
    return {
        1: tables.loan_summary_table(cw),
        3: tables.sources_uses_table(cw),
        4: tables.sponsorship_table(cw),
        8: tables.rent_roll_table(cw),
        9: tables.operating_comparison_table(cw),
        10: tables.sizing_table(cw) + "\n\n**DSCR Sensitivity**\n\n" + tables.dscr_sensitivity_table(cw),
        11: tables.appraisal_table(cw),
        12: tables.third_party_table(cw),
        13: tables.refinance_table(cw),
    }


def build_narrative(cw: CrosswalkData) -> tuple[str, list[str]]:
    facts = build_fact_sheet(cw)
    code = code_sections(cw)
    facts_json = json.dumps(facts, indent=1)
    allowed = allowed_numbers(facts_json, *code.values())

    prose: dict[int, str] = {}
    warnings: list[str] = []
    with ThreadPoolExecutor(max_workers=len(PROSE_GROUPS)) as pool:
        futures = [pool.submit(generate_group, nums, instr, facts_json, allowed) for nums, instr in PROSE_GROUPS]
        for (nums, _), future in zip(PROSE_GROUPS, futures):
            try:
                sections, group_warnings = future.result()
            except Exception as exc:  # keep the memo whole; QC surfaces the warning
                logger.exception("Prose group %s failed", nums)
                sections = {n: "_Commentary unavailable for this section._" for n in nums}
                group_warnings = [f"Sections {nums}: generation failed: {exc}"]
            prose.update(sections)
            warnings.extend(group_warnings)

    parts = [f"**{DISCLAIMER}**"]
    for number, heading in enumerate(HEADINGS, start=1):
        parts.append(f"## {heading}")
        if number in code:
            parts.append(code[number])
        if number in prose:
            parts.append(prose[number])
        if number == 1:
            parts.append("_Tier thresholds reflect Form 4660 (Nov. 2023 redline) values and are unverified "
                         "against the current Form 4660._")
    return "\n\n".join(parts), warnings


def handler(event, context):
    job_id = event["job_id"]
    cw = CrosswalkData.model_validate(s3_utils.read_json(job_id, "crosswalk-data.json"))
    if cw.financing is None or cw.operating_history is None:
        raise ValueError("Crosswalk lacks financing/operating_history; cannot build Lender Narrative")

    narrative, warnings = build_narrative(cw)
    prop = cw.property_identification
    docx_bytes = markdown_to_docx(
        narrative,
        property_name=prop.property_name,
        lender_name=LENDER_NAME,
        title=TITLE,
        location_text=f"{prop.address}, {prop.city}, {prop.state}",
        footer_text=DISCLAIMER,
    )
    s3_utils.write_text(job_id, "sections/lender_narrative.md", narrative)
    s3_utils.write_bytes(
        job_id, "outputs/lender_narrative.docx", docx_bytes,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    s3_utils.write_json(job_id, "sections/lender_narrative_warnings.json", {"warnings": warnings})
    logger.info("Lender narrative complete for %s with %d warnings", job_id, len(warnings))
    return {
        "status": "success",
        "job_id": job_id,
        "s3_key": s3_utils.job_key(job_id, "outputs/lender_narrative.docx"),
        "warnings": warnings,
    }
