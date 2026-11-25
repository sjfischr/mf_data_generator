"""Code-generated Markdown tables for the lender narrative."""

from __future__ import annotations

from lambdas.shared.models import CrosswalkData
from lambdas.shared.underwriting import (
    annual_debt_service,
    remaining_balance,
)


def fmt(value: int | float) -> str:
    if isinstance(value, float):
        return f"${value:,.2f}"
    return f"${value:,}"


def loan_summary_table(crosswalk: CrosswalkData) -> str:
    prop = crosswalk.property_identification
    phys = crosswalk.property_physical
    fin = crosswalk.financing
    if fin is None:
        return "## 1. Loan Summary & Salient Facts\n\nLoan sizing is pending."

    return f"""## 1. Loan Summary & Salient Facts

| Item | Value |
|---|---|
| Property | {prop.property_name}, {prop.address}, {prop.city}, {prop.state} |
| Units | {phys.total_units} |
| Loan Purpose / Execution / Product | {fin.loan_purpose} / {fin.execution} / {fin.product} |
| Tier | {fin.tier} |
| Tier Minimum DSCR / Maximum LTV | {fin.tier_minimum_dscr:.2f}x / {fin.tier_maximum_ltv:.2f}% |
| Loan Amount | {fmt(fin.loan_amount)} |
| Loan Per Unit | {fmt(fin.loan_per_unit)} |
| Note Rate / Underwriting Rate | {fin.note_rate:.2f}% / {fin.underwriting_rate_basis:.2f}% |
| Term / Amortization | {fin.term_months} months / {fin.amortization_months} months |
| Interest-Only / Prepayment | {fin.interest_only_months} months / {fin.prepayment_terms} |
| Appraised Value / Underwriting Value | {fmt(fin.appraised_value)} / {fmt(fin.underwriting_value)} |
| LTV on Appraisal / Underwriting Value | {fin.ltv_appraised_value:.2f}% / {fin.ltv_underwriting_value:.2f}% |
| Underwritten DSCR / Actual DSCR | {fin.underwritten_dscr:.2f}x / {fin.actual_dscr:.2f}x |
| Debt Yield | {fin.debt_yield:.2f}% |
| Breakeven Occupancy | {fin.breakeven_occupancy:.2f}% |
| Binding Constraint | {fin.binding_constraint} |
"""


def sources_and_uses_table(crosswalk: CrosswalkData) -> str:
    fin = crosswalk.financing
    if fin is None or fin.sources_uses is None:
        return "## 3. Sources & Uses\n\nSources and uses pending."

    lines = ["## 3. Sources & Uses", "", "| Sources | Amount |", "|---|---:|"]
    for line in fin.sources_uses.sources:
        lines.append(f"| {line.label} | {fmt(line.amount)} |")
    lines.extend(["", "| Uses | Amount |", "|---|---:|"])
    for line in fin.sources_uses.uses:
        lines.append(f"| {line.label} | {fmt(line.amount)} |")
    return "\n".join(lines)


def operating_comparison_table(crosswalk: CrosswalkData) -> str:
    if crosswalk.operating_history is None:
        return "## 9. Historical Operating Performance vs. Underwriting\n\nOperating history pending."

    hist = crosswalk.operating_history
    columns = [
        ("Year 3", hist.year_3),
        ("Year 2", hist.year_2),
        ("Year 1", hist.year_1),
        ("Underwritten", hist.underwritten),
    ]
    rows = [
        ("GPR", "gpr"),
        ("Vacancy", "vacancy"),
        ("Concessions", "concessions"),
        ("Bad Debt", "bad_debt"),
        ("Other Income", "other_income"),
        ("Effective Gross Income", "effective_gross_income"),
        ("Total Operating Expenses", "total_operating_expenses"),
        ("NOI", "noi"),
        ("Replacement Reserves", "replacement_reserves"),
        ("NCF", "ncf"),
    ]
    lines = [
        "## 9. Historical Operating Performance vs. Underwriting",
        "",
        "| Category | Year 3 | Year 2 | Year 1 | Underwritten |",
        "|---|---:|---:|---:|---:|",
    ]
    for label, field in rows:
        values = []
        for _, column in columns:
            value = getattr(column, field)
            if callable(value):
                value = value()
            values.append(f"{fmt(value)}")
        lines.append(f"| {label} | {values[0]} | {values[1]} | {values[2]} | {values[3]} |")
    return "\n".join(lines)


def sizing_table(crosswalk: CrosswalkData) -> str:
    fin = crosswalk.financing
    if fin is None:
        return "## 10. Underwritten NCF & Loan Sizing\n\nLoan sizing pending."

    uw = (
        crosswalk.operating_history.underwritten
        if crosswalk.operating_history
        else None
    )
    ncf = uw.ncf if uw else 0
    return f"""## 10. Underwritten NCF & Loan Sizing

| Metric | Value |
|---|---:|
| Underwritten NCF | {fmt(ncf)} |
| DSCR-Constrained Amount | {fmt(fin.dscr_constrained_amount)} |
| LTV-Constrained Amount | {fmt(fin.ltv_constrained_amount)} |
| Final Loan Amount | {fmt(fin.loan_amount)} |
| Binding Constraint | {fin.binding_constraint} |
| Annual Debt Service — Note Rate | {fmt(fin.annual_debt_service_note)} |
| Annual Debt Service — Underwriting Rate | {fmt(fin.annual_debt_service_underwriting)} |
"""


def appraisal_reconciliation_table(crosswalk: CrosswalkData) -> str:
    fin = crosswalk.financial_data
    val = crosswalk.valuation
    uw = (
        crosswalk.operating_history.underwritten
        if crosswalk.operating_history
        else None
    )
    return f"""## 11. Appraisal Review

| Metric | Appraiser / Pro Forma | Lender Underwritten |
|---|---:|---:|
| Effective Gross Income | {fmt(fin.pro_forma_income.effective_gross_income)} | {fmt(uw.effective_gross_income if uw else 0)} |
| Operating Expenses | {fmt(fin.pro_forma_expenses.total_operating_expenses)} | {fmt(uw.total_operating_expenses if uw else 0)} |
| NOI | {fmt(fin.net_operating_income)} | {fmt(uw.noi if uw else 0)} |
| Reserves / NCF | {fmt(fin.pro_forma_expenses.replacement_reserves)} / {fmt(fin.net_operating_income - fin.pro_forma_expenses.replacement_reserves)} | {fmt(uw.replacement_reserves if uw else 0)} / {fmt(uw.ncf if uw else 0)} |
| Appraised Value | {fmt(val.final_value_conclusion.market_value)} | — |
"""


def dscr_sensitivity_table(crosswalk: CrosswalkData) -> str:
    fin = crosswalk.financing
    if fin is None:
        return "| DSCR Sensitivity | Loan Amount |"
    uw = crosswalk.operating_history.underwritten if crosswalk.operating_history else None
    ncf = uw.ncf if uw else 0
    lines = [
        "| Interest Rate | Debt Service | DSCR |",
        "|---|---:|---:|",
    ]
    for bps in (0, 100, 200):
        rate = fin.note_rate + bps / 100
        debt = annual_debt_service(
            fin.loan_amount,
            rate,
            fin.amortization_months,
        )
        dscr = ncf / debt if debt else 0
        lines.append(f"| {rate:.2f}% | {fmt(debt)} | {dscr:.2f}x |")
    return "\n".join(lines)


def refinance_risk_table(crosswalk: CrosswalkData) -> str:
    fin = crosswalk.financing
    if fin is None:
        return "## 13. Refinance Risk Analysis\n\nRefinance risk pending."
    uw = crosswalk.operating_history.underwritten if crosswalk.operating_history else None
    ncf = uw.ncf if uw else 0
    maturity_month = fin.term_months
    mature_year = max(1, maturity_month // 12)
    projected_ncf = round(ncf * (1.02 ** (mature_year - 1)))
    balance = remaining_balance(
        fin.loan_amount,
        fin.note_rate,
        fin.amortization_months,
        fin.term_months,
    )
    refinance_rate = fin.note_rate + 1.0
    refinance_dscr = projected_ncf / (
        annual_debt_service(balance, refinance_rate, fin.amortization_months)
    ) if balance else 0
    return f"""## 13. Refinance Risk Analysis

| Metric | Value |
|---|---:|
| Projected Year {mature_year} NCF (2% annual income growth) | {fmt(projected_ncf)} |
| Balloon Balance at Month {maturity_month} | {fmt(balance)} |
| Refinance Rate Assumption | {refinance_rate:.2f}% |
| Refinance DSCR | {refinance_dscr:.2f}x |
"""
