"""Code-generated Markdown tables for the Lender Narrative (no LLM figures)."""

from __future__ import annotations

from lambdas.shared.models import CrosswalkData, OperatingColumn
from lambdas.shared.underwriting import annual_debt_service, remaining_balance

REFI_RATE_SPREAD = 1.0  # refinance-rate assumption: note rate + 100 bps
INCOME_GROWTH = 0.02
TAX_GROWTH = 0.03
EXPENSE_GROWTH = 0.02

OPERATING_ROWS = [
    ("Gross Potential Rent", "gpr", 1),
    ("Loss / Gain to Lease", "loss_gain_to_lease", 1),
    ("Vacancy", "vacancy", -1),
    ("Concessions", "concessions", -1),
    ("Bad Debt", "bad_debt", -1),
    ("Non-Revenue Units", "non_revenue_units", -1),
    ("**Net Rental Income**", "net_rental_income", 1),
    ("Laundry / Vending", "laundry_vending", 1),
    ("Parking", "parking", 1),
    ("Commercial", "commercial", 1),
    ("Other Income", "other_income", 1),
    ("**Effective Gross Income**", "effective_gross_income", 1),
    ("Real Estate Taxes", "real_estate_taxes", 1),
    ("Insurance", "insurance", 1),
    ("Utilities", "utilities", 1),
    ("Water & Sewer", "water_sewer", 1),
    ("Repairs & Maintenance", "repairs_maintenance", 1),
    ("Payroll & Benefits", "payroll_benefits", 1),
    ("General & Administrative", "general_administrative", 1),
    ("Marketing", "marketing", 1),
    ("Professional Fees", "professional_fees", 1),
    ("Management Fee", "management_fee", 1),
    ("Ground Rent", "ground_rent", 1),
    ("Other Expenses", "other_expenses", 1),
    ("**Total Operating Expenses**", "total_operating_expenses", 1),
    ("**Net Operating Income**", "noi", 1),
    ("Replacement Reserves", "replacement_reserves", 1),
    ("**Net Cash Flow**", "ncf", 1),
]


def money(value: float) -> str:
    value = round(value)
    return f"-${abs(value):,}" if value < 0 else f"${value:,}"


def pct(value: float) -> str:
    return f"{value:.2f}%"


def ratio(value: float) -> str:
    return f"{value:.2f}x"


def _table(headers: list[str], rows: list[list[str]], align: str | None = None) -> str:
    align = align or ("|---" + "|---:" * (len(headers) - 1) + "|")
    lines = ["| " + " | ".join(headers) + " |", align]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def loan_summary_table(cw: CrosswalkData) -> str:
    prop, phys, fin = cw.property_identification, cw.property_physical, cw.financing
    uw = cw.operating_history.underwritten
    rows = [
        ["Property", f"{prop.property_name}, {prop.address}, {prop.city}, {prop.state} {prop.zip}"],
        ["Units / Year Built", f"{phys.total_units} / {prop.year_built} ({phys.building_type})"],
        ["Loan Purpose / Execution / Product", f"{fin.loan_purpose} / {fin.execution} / {fin.product}"],
        ["Pricing / Underwriting Tier", f"{fin.tier} (min DSCR {ratio(fin.tier_minimum_dscr)}, max LTV {pct(fin.tier_maximum_ltv)})"],
        ["Loan Amount", money(fin.loan_amount)],
        ["Loan Per Unit", money(fin.loan_per_unit)],
        ["Note Rate / Underwriting Rate Basis", f"{pct(fin.note_rate)} / {pct(fin.underwriting_rate_basis)}"],
        ["Term / Amortization / Interest-Only", f"{fin.term_months} months / {fin.amortization_months} months / {fin.interest_only_months} months"],
        ["Prepayment", fin.prepayment_terms],
        ["Appraised Value / Underwriting Value", f"{money(fin.appraised_value)} / {money(fin.underwriting_value)}"],
        ["LTV (Underwriting / Appraised)", f"{pct(fin.ltv_underwriting_value)} / {pct(fin.ltv_appraised_value)}"],
        ["Underwritten DSCR / Actual DSCR", f"{ratio(fin.underwritten_dscr)} / {ratio(fin.actual_dscr)}"],
        ["Debt Yield", pct(fin.debt_yield)],
        ["Breakeven Occupancy", pct(fin.breakeven_occupancy)],
        ["Underwritten NOI / NCF", f"{money(uw.noi)} / {money(uw.ncf)}"],
        ["Replacement Reserve", f"{money(uw.replacement_reserves / phys.total_units)} per unit per year"],
        ["Binding Constraint", fin.binding_constraint],
    ]
    return _table(["Item", "Value"], rows, "|---|---|")


def sources_uses_table(cw: CrosswalkData) -> str:
    su = cw.financing.sources_uses
    rows = [[line.label, money(line.amount)] for line in su.sources]
    rows.append(["**Total Sources**", f"**{money(sum(l.amount for l in su.sources))}**"])
    uses = [[line.label, money(line.amount)] for line in su.uses]
    uses.append(["**Total Uses**", f"**{money(sum(l.amount for l in su.uses))}**"])
    return _table(["Sources", "Amount"], rows) + "\n\n" + _table(["Uses", "Amount"], uses)


def sponsorship_table(cw: CrosswalkData) -> str:
    sp = cw.sponsorship
    rows = [[p.name, p.role, str(p.years_experience), f"{p.units_owned:,}", money(p.net_worth), money(p.liquidity)]
            for p in sp.key_principals]
    return (
        f"**Borrower:** {sp.borrower_name} ({sp.borrower_type})  \n**Guarantor:** {sp.guarantor}\n\n"
        + _table(["Key Principal", "Role", "Years", "Units Owned", "Net Worth", "Liquidity"], rows,
                 "|---|---|---:|---:|---:|---:|")
    )


def rent_roll_table(cw: CrosswalkData) -> str:
    fin = cw.financial_data
    rows = []
    for item in cw.property_physical.unit_mix:
        market = fin.market_rents_monthly.get(item.unit_type, 0)
        in_place = fin.in_place_rents_monthly.get(item.unit_type, 0)
        rows.append([item.unit_type, str(item.count), f"{item.avg_size_sf:,}", money(market), money(in_place),
                     pct((in_place - market) / market * 100 if market else 0)])
    occ = fin.occupancy
    return (
        _table(["Unit Type", "Units", "Avg SF", "Market Rent", "In-Place Rent", "In-Place vs Market"], rows)
        + f"\n\nPhysical occupancy {pct(occ.physical_percent)} ({occ.occupied_units} occupied / "
          f"{occ.vacant_units} vacant) as of {fin.effective_date}."
    )


def _value(column: OperatingColumn, field: str) -> int:
    return getattr(column, field)


def operating_comparison_table(cw: CrosswalkData) -> str:
    hist = cw.operating_history
    units = cw.property_physical.total_units
    uw_egi = hist.underwritten.effective_gross_income
    rows = []
    for label, field, sign in OPERATING_ROWS:
        values = [sign * _value(col, field) for col in (hist.year_3, hist.year_2, hist.year_1, hist.underwritten)]
        y1, uw = values[2], values[3]
        variance = pct((uw - y1) / abs(y1) * 100) if y1 else "n/a"
        rows.append([label] + [money(v) for v in values] + [money(uw / units), pct(uw / uw_egi * 100), variance])
    return _table(["Category", "Year 3", "Year 2", "Year 1", "Underwritten", "UW / Unit", "UW % EGI", "UW vs Y1"], rows)


def material_variances(cw: CrosswalkData) -> list[str]:
    hist = cw.operating_history
    out = []
    for label, field, _ in OPERATING_ROWS:
        y1, uw = _value(hist.year_1, field), _value(hist.underwritten, field)
        if y1 and abs(uw - y1) / abs(y1) > 0.05:
            out.append(f"{label.strip('*')}: Year 1 {money(y1)} vs Underwritten {money(uw)} "
                       f"(change {money(uw - y1)}, {pct((uw - y1) / abs(y1) * 100)})")
    return out


def sizing_table(cw: CrosswalkData) -> str:
    fin, uw = cw.financing, cw.operating_history.underwritten
    rows = [
        ["Underwritten NCF", money(uw.ncf)],
        [f"DSCR-Constrained Amount (min {ratio(fin.tier_minimum_dscr)} @ {pct(fin.underwriting_rate_basis)})", money(fin.dscr_constrained_amount)],
        [f"LTV-Constrained Amount ({pct(fin.tier_maximum_ltv)} of {money(fin.underwriting_value)})", money(fin.ltv_constrained_amount)],
        ["**Final Loan Amount** (lesser, rounded down to $1,000)", f"**{money(fin.loan_amount)}**"],
        ["Binding Constraint", fin.binding_constraint],
        ["Annual Debt Service @ Note Rate", money(fin.annual_debt_service_note)],
        ["Annual Debt Service @ Underwriting Rate", money(fin.annual_debt_service_underwriting)],
    ]
    return _table(["Metric", "Value"], rows)


def dscr_sensitivity(cw: CrosswalkData) -> list[tuple[float, int, float]]:
    fin, ncf = cw.financing, cw.operating_history.underwritten.ncf
    out = []
    for bps in (0, 100, 200):
        rate = fin.note_rate + bps / 100
        debt = annual_debt_service(fin.loan_amount, rate, fin.amortization_months)
        out.append((rate, debt, ncf / debt if debt else 0.0))
    return out


def dscr_sensitivity_table(cw: CrosswalkData) -> str:
    rows = [[f"{label} ({pct(rate)})", money(debt), ratio(dscr)]
            for label, (rate, debt, dscr) in zip(["Note rate", "+100 bps", "+200 bps"], dscr_sensitivity(cw))]
    return _table(["Rate Scenario", "Annual Debt Service", "DSCR"], rows)


def appraisal_table(cw: CrosswalkData) -> str:
    fin, val, uw = cw.financial_data, cw.valuation, cw.operating_history.underwritten
    exp = fin.pro_forma_expenses
    rows = [
        ["Effective Gross Income", money(fin.pro_forma_income.effective_gross_income), money(uw.effective_gross_income)],
        ["Operating Expenses (excl. reserves)", money(exp.total_operating_expenses - exp.replacement_reserves), money(uw.total_operating_expenses)],
        ["Replacement Reserves", money(exp.replacement_reserves), money(uw.replacement_reserves)],
        ["NOI (appraiser, after reserves) / NOI (lender, before reserves)", money(fin.net_operating_income), money(uw.noi)],
        ["Net Cash Flow", money(fin.net_operating_income), money(uw.ncf)],
        ["Capitalization Rate", pct(val.income_approach.cap_rate), "—"],
        ["Value", money(val.final_value_conclusion.market_value), money(cw.financing.underwriting_value) + " (underwriting value)"],
    ]
    return _table(["Metric", "Appraiser Pro Forma", "Lender Underwritten"], rows, "|---|---:|---:|")


def third_party_table(cw: CrosswalkData) -> str:
    tpr = cw.third_party_reports
    pca, esa = tpr.property_condition_assessment, tpr.environmental_site_assessment
    rows = [
        ["Appraisal", tpr.appraisal.firm, tpr.appraisal.date, f"Market value {money(tpr.appraisal.value)}"],
        ["Property Condition Assessment", pca.firm, pca.date,
         f"Immediate repairs {money(pca.immediate_repairs)}; 12-year reserve need {money(pca.twelve_year_reserve_need)}"],
        ["Phase I ESA", esa.firm, esa.date, esa.finding],
        ["Seismic", "—", "—", "Required" if tpr.seismic_applicable else "Not required (low seismic risk zone)"],
        ["Zoning", "—", "—", tpr.zoning_status],
    ]
    return _table(["Report", "Firm", "Date", "Conclusion"], rows, "|---|---|---|---|")


def refinance_projection(cw: CrosswalkData) -> dict:
    fin, uw = cw.financing, cw.operating_history.underwritten
    years = max(1, fin.term_months // 12)
    egi = uw.effective_gross_income * (1 + INCOME_GROWTH) ** (years - 1)
    taxes = uw.real_estate_taxes * (1 + TAX_GROWTH) ** (years - 1)
    other_opex = (uw.total_operating_expenses - uw.real_estate_taxes) * (1 + EXPENSE_GROWTH) ** (years - 1)
    ncf = round(egi - taxes - other_opex - uw.replacement_reserves)
    balloon = remaining_balance(fin.loan_amount, fin.note_rate, fin.amortization_months,
                                max(0, fin.term_months - fin.interest_only_months))
    refi_rate = fin.note_rate + REFI_RATE_SPREAD
    refi_debt = annual_debt_service(balloon, refi_rate, 360)
    return {
        "year": years, "ncf": ncf, "balloon": balloon, "refi_rate": refi_rate,
        "refi_debt_service": refi_debt, "refi_dscr": ncf / refi_debt if refi_debt else 0.0,
    }


def refinance_table(cw: CrosswalkData) -> str:
    r = refinance_projection(cw)
    rows = [
        [f"Projected Year {r['year']} NCF (income +2%/yr, taxes +3%/yr, other expenses +2%/yr, constant vacancy)", money(r["ncf"])],
        [f"Balloon Balance at Month {cw.financing.term_months}", money(r["balloon"])],
        ["Refinance Rate Assumption (note rate + 100 bps, 30-year amortization)", pct(r["refi_rate"])],
        ["Refinance Debt Service", money(r["refi_debt_service"])],
        ["Refinance DSCR", ratio(r["refi_dscr"])],
    ]
    return _table(["Metric", "Value"], rows)
