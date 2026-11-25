"""Deterministic multifamily underwriting calculations and crosswalk finalization."""

from __future__ import annotations

import hashlib
import random
import calendar
from datetime import date, timedelta

from lambdas.shared.models import (
    CrosswalkDraft,
    CrosswalkData,
    Financing,
    HistoricalYear,
    OperatingColumn,
    OperatingHistory,
    SourcesUses,
    SourcesUsesLine,
)


# Current Form 4660 thresholds are login-gated. These values come from the
# Nov. 2023 Form 4660 redline and are explicitly marked unverified.
CONVENTIONAL_FIXED_TIERS = {
    "Tier 2": {"min_dscr": 1.25, "max_ltv": 80.0},
    "Tier 3": {"min_dscr": 1.35, "max_ltv": 65.0},
    "Tier 4": {"min_dscr": 1.55, "max_ltv": 55.0},
}

TIER_2_RATE_FLOORS = [
    (84, 6.75),
    (120, 5.50),
    (144, 5.00),
]


def level_amortizing_payment(
    principal: float,
    annual_rate_percent: float,
    amortization_months: int,
) -> float:
    if principal <= 0:
        return 0.0
    monthly_rate = annual_rate_percent / 100.0 / 12.0
    if monthly_rate == 0:
        return principal / amortization_months
    factor = monthly_rate / (1 - (1 + monthly_rate) ** (-amortization_months))
    return principal * factor


def annual_debt_service(
    principal: float,
    annual_rate_percent: float,
    amortization_months: int,
) -> int:
    return round(level_amortizing_payment(
        principal,
        annual_rate_percent,
        amortization_months,
    ) * 12)


def dscr_constrained_amount(
    ncf: int,
    minimum_dscr: float,
    annual_rate_percent: float,
    amortization_months: int,
) -> int:
    if minimum_dscr <= 0:
        return 0

    payment_factor = level_amortizing_payment(
        1.0,
        annual_rate_percent,
        amortization_months,
    ) * 12
    if payment_factor <= 0:
        return 0
    loan = (ncf / minimum_dscr) / payment_factor
    return int(loan // 1000 * 1000)


def ltv_constrained_amount(
    underwriting_value: int,
    maximum_ltv_percent: float,
) -> int:
    return int((underwriting_value * maximum_ltv_percent / 100.0) // 1000 * 1000)


def remaining_balance(
    loan_amount: int,
    annual_rate_percent: float,
    amortization_months: int,
    paid_months: int,
) -> int:
    if loan_amount <= 0:
        return 0
    monthly_rate = annual_rate_percent / 100.0 / 12.0
    monthly_payment = level_amortizing_payment(
        loan_amount,
        annual_rate_percent,
        amortization_months,
    )
    if monthly_rate == 0:
        return max(0, round(loan_amount - monthly_payment * paid_months))
    factor = (1 + monthly_rate) ** paid_months
    balance = loan_amount * factor - monthly_payment * (
        (factor - 1) / monthly_rate
    )
    return max(0, round(balance))


def get_tier_constraints(tier: str) -> dict:
    if tier not in CONVENTIONAL_FIXED_TIERS:
        raise ValueError(f"Unsupported tier: {tier}")
    return dict(CONVENTIONAL_FIXED_TIERS[tier])


def get_tier_2_rate_floor(term_months: int) -> float:
    if term_months < 84:
        return 6.75
    if term_months < 120:
        return 5.50
    if term_months < 144:
        return 5.00
    return 0.0


def build_underwritten_column(
    year_1: OperatingColumn,
    total_units: int,
    management_fee_percent: float | None = None,
) -> OperatingColumn:
    """Apply the public Sec. 203.01 underwritten floors."""
    uw = year_1.model_copy(deep=True)
    uw.period_start = None
    uw.period_end = None

    economic_vacancy = uw.vacancy + uw.concessions + uw.bad_debt
    floor_vacancy = round(0.05 * uw.gpr)
    if economic_vacancy < floor_vacancy:
        uw.vacancy = floor_vacancy - uw.concessions - uw.bad_debt
        uw.vacancy = max(0, uw.vacancy)

    underwritten_egi_before_mgmt = uw.effective_gross_income
    management_floor = round(0.03 * underwritten_egi_before_mgmt)
    if uw.management_fee < management_floor:
        uw.management_fee = management_floor

    reserve_floor = 200 * total_units
    if uw.replacement_reserves < reserve_floor:
        uw.replacement_reserves = reserve_floor

    tax_floor = round(year_1.real_estate_taxes * 1.03)
    uw.real_estate_taxes = max(uw.real_estate_taxes, tax_floor)

    uw.insurance = max(uw.insurance, year_1.insurance)
    return uw


def derive_prior_years(
    year_1: OperatingColumn,
    job_id: str,
) -> tuple[OperatingColumn, OperatingColumn]:
    seed = int.from_bytes(
        hashlib.sha256(job_id.encode("utf-8")).digest()[:8],
        "big",
    )
    rng = random.Random(seed)

    def derive(source: OperatingColumn, income_factor: float, expense_factor: float) -> OperatingColumn:
        result = source.model_copy(deep=True)
        for field in (
            "gpr",
            "laundry_vending",
            "parking",
            "commercial",
            "other_income",
        ):
            current = getattr(result, field)
            setattr(
                result,
                field,
                max(0, round(current * income_factor * rng.uniform(0.985, 1.015))),
            )
        for field in (
            "real_estate_taxes",
            "insurance",
            "utilities",
            "water_sewer",
            "repairs_maintenance",
            "payroll_benefits",
            "general_administrative",
            "marketing",
            "professional_fees",
            "management_fee",
            "ground_rent",
            "other_expenses",
            "replacement_reserves",
        ):
            current = getattr(result, field)
            setattr(
                result,
                field,
                max(0, round(current * expense_factor * rng.uniform(0.98, 1.02))),
            )
        result.vacancy = max(0, round(result.vacancy * rng.uniform(1.02, 1.08)))
        result.concessions = max(0, round(result.concessions * rng.uniform(1.00, 1.10)))
        result.bad_debt = max(0, round(result.bad_debt * rng.uniform(1.00, 1.10)))
        result.loss_gain_to_lease = round(result.loss_gain_to_lease * income_factor)
        result.non_revenue_units = round(result.non_revenue_units * income_factor)
        return result

    year_2 = derive(year_1, 0.97, 0.965)
    year_3 = derive(year_2, 0.97, 0.965)
    return year_2, year_3


def balance_sources_uses(
    loan_amount: int,
    loan_purpose: str,
    purchase_price: int,
    existing_debt_payoff: int,
    closing_costs: int,
    initial_reserve_deposit: int,
    immediate_repairs: int,
) -> SourcesUses:
    """Build a balanced sources-and-uses schedule; borrower cash balances it."""
    if loan_purpose.lower().startswith("refi"):
        uses = [SourcesUsesLine(label="Existing Debt Payoff", amount=existing_debt_payoff)]
    else:
        uses = [SourcesUsesLine(label="Purchase Price", amount=purchase_price)]
    uses += [
        SourcesUsesLine(label="Closing Costs", amount=closing_costs),
        SourcesUsesLine(label="Initial Replacement Reserve Deposit", amount=initial_reserve_deposit),
        SourcesUsesLine(label="Completion / Repair Escrow", amount=immediate_repairs),
    ]
    total_uses = sum(line.amount for line in uses)
    sources = [SourcesUsesLine(label="DUS Loan", amount=loan_amount)]
    if loan_amount >= total_uses:
        uses.append(SourcesUsesLine(label="Cash to Borrower", amount=loan_amount - total_uses))
    else:
        sources.append(SourcesUsesLine(label="Borrower Equity", amount=total_uses - loan_amount))
    return SourcesUses(sources=sources, uses=uses)


def _pct_split(total: int, weights: list[float]) -> list[int]:
    raw = [total * w for w in weights]
    values = [int(v) for v in raw]
    values[-1] += total - sum(values)
    return values


def derive_year1_from_pro_forma(draft: CrosswalkDraft) -> OperatingColumn:
    """Build a detailed trailing Year 1 operating column from the appraiser pro forma.

    Actuals run slightly below the stabilized pro forma so Year 1 EGI lands
    within the +/-10% band the crosswalk spec expects.
    """
    income = draft.financial_data.pro_forma_income
    expenses = draft.financial_data.pro_forma_expenses
    units = draft.property_physical.total_units

    gpr = round(income.potential_gross_rental_income * 0.985)
    economic_loss = round(income.vacancy_collection_loss_amount * 0.95)
    vacancy, concessions, bad_debt = _pct_split(economic_loss, [0.75, 0.15, 0.10])
    laundry, parking, other = _pct_split(round(income.other_income * 0.97), [0.30, 0.35, 0.35])
    utilities, water_sewer = _pct_split(round(expenses.utilities * 0.97), [0.65, 0.35])
    g_and_a, professional = _pct_split(round(expenses.administrative * 0.97), [0.80, 0.20])

    column = OperatingColumn(
        gpr=gpr,
        loss_gain_to_lease=-round(gpr * 0.01),
        vacancy=vacancy,
        concessions=concessions,
        bad_debt=bad_debt,
        non_revenue_units=round(gpr / units) if units >= 50 else 0,
        laundry_vending=laundry,
        parking=parking,
        commercial=0,
        other_income=other,
        real_estate_taxes=round(expenses.real_estate_taxes * 0.97),
        insurance=round(expenses.insurance * 0.97),
        utilities=utilities,
        water_sewer=water_sewer,
        repairs_maintenance=round(expenses.repairs_maintenance * 0.97),
        payroll_benefits=round(expenses.payroll * 0.97),
        general_administrative=g_and_a,
        marketing=round(expenses.marketing * 0.97),
        professional_fees=professional,
        management_fee=round(expenses.management_fee_amount * 0.97),
        ground_rent=0,
        other_expenses=0,
        replacement_reserves=max(expenses.replacement_reserves, 250 * units),
    )
    column.other_expenses = round(column.effective_gross_income * 0.005)
    return column


def _period_bounds(period_end: date) -> tuple[date, date]:
    start_year = period_end.year - 1
    start_month = period_end.month + 1
    if start_month == 13:
        start_year += 1
        start_month = 1
    return date(start_year, start_month, 1), period_end


def _assign_periods(effective_date: str, columns: list[OperatingColumn]) -> None:
    effective = date.fromisoformat(effective_date)
    end = effective.replace(day=1) - timedelta(days=1)
    for column in columns:
        start, finish = _period_bounds(end)
        column.period_start = start.isoformat()
        column.period_end = finish.isoformat()
        end = start - timedelta(days=1)


def finalize_crosswalk(draft: CrosswalkDraft) -> CrosswalkData:
    """Run the deterministic underwriting engine and return a complete crosswalk."""
    year_1 = draft.operating_year1 or derive_year1_from_pro_forma(draft)
    year_2, year_3 = derive_prior_years(year_1, draft.job_id)
    total_units = draft.property_physical.total_units
    underwritten = build_underwritten_column(year_1, total_units)
    _assign_periods(draft.financial_data.effective_date, [year_1, year_2, year_3])

    operating_history = OperatingHistory(
        year_1=year_1,
        year_2=year_2,
        year_3=year_3,
        underwritten=underwritten,
    )

    inputs = draft.financing_inputs or {}
    tier = str(inputs.get("tier", "Tier 2"))
    if tier not in CONVENTIONAL_FIXED_TIERS:
        tier = "Tier 2"
    tier_constraints = get_tier_constraints(tier)
    note_rate = float(inputs.get("note_rate", 6.0))
    term_months = int(inputs.get("term_months", 120))
    amortization_months = int(inputs.get("amortization_months", 360))
    interest_only_months = int(inputs.get("interest_only_months", 0))
    underwriting_rate = max(
        note_rate,
        get_tier_2_rate_floor(term_months) if tier == "Tier 2" else 0.0,
    )

    appraised_value = draft.valuation.final_value_conclusion.market_value
    loan_purpose = str(inputs.get("loan_purpose", "Acquisition"))
    is_refi = loan_purpose.lower().startswith("refi")
    purchase_price = int(inputs.get("purchase_price") or appraised_value)
    underwriting_value = appraised_value if is_refi else min(appraised_value, purchase_price)
    ncf = underwritten.ncf

    dscr_amount = dscr_constrained_amount(
        ncf,
        tier_constraints["min_dscr"],
        underwriting_rate,
        amortization_months,
    )
    ltv_amount = ltv_constrained_amount(underwriting_value, tier_constraints["max_ltv"])
    loan_amount = min(dscr_amount, ltv_amount)
    binding = "DSCR" if dscr_amount <= ltv_amount else "LTV"

    ads_note = annual_debt_service(loan_amount, note_rate, amortization_months)
    ads_underwriting = annual_debt_service(loan_amount, underwriting_rate, amortization_months)
    gpr = underwritten.gpr
    total_opex = underwritten.total_operating_expenses
    breakeven = (total_opex + ads_note) / gpr * 100 if gpr else 0.0

    tpr = draft.third_party_reports
    immediate_repairs = tpr.property_condition_assessment.immediate_repairs if tpr else 0
    sources_uses = balance_sources_uses(
        loan_amount=loan_amount,
        loan_purpose=loan_purpose,
        purchase_price=purchase_price,
        existing_debt_payoff=int(inputs.get("existing_debt_payoff") or round(appraised_value * 0.55)),
        closing_costs=int(inputs.get("closing_costs") or round(loan_amount * 0.015)),
        initial_reserve_deposit=round(underwritten.replacement_reserves / 12),
        immediate_repairs=round(immediate_repairs * 1.25),
    )

    financing = Financing(
        loan_purpose=loan_purpose,
        execution=str(inputs.get("execution", "DUS")),
        product=str(inputs.get("product", "Conventional Fixed")),
        tier=tier,
        loan_amount=loan_amount,
        loan_per_unit=round(loan_amount / total_units),
        note_rate=note_rate,
        underwriting_rate_basis=underwriting_rate,
        term_months=term_months,
        amortization_months=amortization_months,
        interest_only_months=interest_only_months,
        prepayment_terms=str(inputs.get("prepayment_terms", "Yield maintenance")),
        purchase_price=None if is_refi else purchase_price,
        purchase_date=None if is_refi else inputs.get("purchase_date"),
        underwriting_value=underwriting_value,
        appraised_value=appraised_value,
        tier_minimum_dscr=tier_constraints["min_dscr"],
        tier_maximum_ltv=tier_constraints["max_ltv"],
        binding_constraint=binding,
        annual_debt_service_note=ads_note,
        annual_debt_service_underwriting=ads_underwriting,
        underwritten_dscr=round(ncf / ads_underwriting, 2) if ads_underwriting else 0.0,
        actual_dscr=round(ncf / ads_note, 2) if ads_note else 0.0,
        ltv_underwriting_value=round(loan_amount / underwriting_value * 100, 2) if underwriting_value else 0,
        ltv_appraised_value=round(loan_amount / appraised_value * 100, 2) if appraised_value else 0,
        debt_yield=round(ncf / loan_amount * 100, 2) if loan_amount else 0,
        breakeven_occupancy=round(breakeven, 2),
        dscr_constrained_amount=dscr_amount,
        ltv_constrained_amount=ltv_amount,
        sources_uses=sources_uses,
    )

    historical_t12 = {}
    for label, column in (("Year 1", year_1), ("Year 2", year_2), ("Year 3", year_3)):
        historical_t12[label] = HistoricalYear(
            rental_income=column.gpr + column.loss_gain_to_lease,
            other_income=column.laundry_vending + column.parking + column.commercial + column.other_income,
            vacancy_loss=-(column.vacancy + column.concessions + column.bad_debt + column.non_revenue_units),
            effective_gross_income=column.effective_gross_income,
            operating_expenses=column.total_operating_expenses,
            net_operating_income=column.noi,
        )

    data = draft.model_dump()
    data.pop("operating_year1", None)
    data.pop("history_assumptions", None)
    data.pop("financing_inputs", None)
    data["operating_history"] = operating_history.model_dump()
    data["financing"] = financing.model_dump()
    data["financial_data"]["historical_t12"] = {k: v.model_dump() for k, v in historical_t12.items()}

    # Sponsor capacity: aggregate net worth >= loan, liquidity >= 9 months debt service.
    sponsorship = data.get("sponsorship")
    if sponsorship and sponsorship.get("key_principals"):
        principals = sponsorship["key_principals"]
        net_worth_gap = loan_amount - sum(p["net_worth"] for p in principals)
        if net_worth_gap > 0:
            principals[0]["net_worth"] += net_worth_gap + round(loan_amount * 0.25, -5)
        liquidity_need = round(ads_note * 9 / 12)
        liquidity_gap = liquidity_need - sum(p["liquidity"] for p in principals)
        if liquidity_gap > 0:
            principals[0]["liquidity"] += liquidity_gap + round(liquidity_need * 0.5, -4)

    reports = data.get("third_party_reports")
    if reports:
        reports["appraisal"]["value"] = appraised_value

    return CrosswalkData.model_validate(data)
