"""Deterministic multifamily underwriting calculations and crosswalk finalization."""

from __future__ import annotations

import hashlib
import random
import calendar
from datetime import date

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

    year_2 = derive(year_1, 0.985, 0.97)
    year_3 = derive(year_2, 0.985, 0.97)
    return year_2, year_3


def balance_sources_uses(
    loan_amount: int,
    purchase_price: int,
    closing_costs: int,
    reserves: int,
    initial_cash_equity: int,
) -> SourcesUses:
    uses = [
        SourcesUsesLine(label="Purchase Price", amount=purchase_price),
        SourcesUsesLine(label="Closing Costs", amount=closing_costs),
        SourcesUsesLine(label="Initial Replacement Reserve", amount=reserves),
    ]
    total_uses = sum(line.amount for line in uses)
    cash_to_borrower = max(0, loan_amount + initial_cash_equity - total_uses)
    if cash_to_borrower:
        uses.append(SourcesUsesLine(label="Cash to Borrower", amount=cash_to_borrower))
    else:
        uses.append(SourcesUsesLine(label="Borrower Cash Required", amount=max(0, total_uses - loan_amount)))

    sources = [
        SourcesUsesLine(label="DUS Loan", amount=loan_amount),
        SourcesUsesLine(label="Borrower Cash", amount=max(0, initial_cash_equity)),
    ]
    return SourcesUses(sources=sources, uses=uses)


def finalize_crosswalk(draft: CrosswalkDraft) -> CrosswalkData:
    """Run the deterministic underwriting engine and return a complete crosswalk."""
    year_1 = draft.operating_year1 or OperatingColumn()
    if draft.operating_year1 is None:
        income = draft.financial_data.pro_forma_income
        expenses = draft.financial_data.pro_forma_expenses
        year_1 = OperatingColumn(
            gpr=income.potential_gross_rental_income,
            laundry_vending=0,
            parking=0,
            commercial=0,
            other_income=income.other_income,
            real_estate_taxes=expenses.real_estate_taxes,
            insurance=expenses.insurance,
            utilities=expenses.utilities,
            water_sewer=0,
            repairs_maintenance=expenses.repairs_maintenance,
            payroll_benefits=expenses.payroll,
            general_administrative=expenses.administrative,
            marketing=expenses.marketing,
            professional_fees=0,
            management_fee=expenses.management_fee_amount,
            ground_rent=0,
            other_expenses=0,
            replacement_reserves=expenses.replacement_reserves,
        )
    year_2, year_3 = derive_prior_years(year_1, draft.job_id)
    underwritten = build_underwritten_column(
        year_1,
        draft.property_physical.total_units,
    )
    try:
        effective = date.fromisoformat(draft.financial_data.effective_date)
        year_1_end = effective.replace(day=1) - __import__("datetime").timedelta(days=1)
        year_1_start = date(
            year_1_end.year - 1,
            year_1_end.month,
            1,
        )
        year_2_end = date(year_1_end.year - 1, year_1_end.month, calendar.monthrange(year_1_end.year - 1, year_1_end.month)[1])
        year_2_start = date(year_2_end.year - 1, year_2_end.month, 1)
        year_3_end = date(year_2_end.year - 1, year_2_end.month, calendar.monthrange(year_2_end.year - 1, year_2_end.month)[1])
        year_3_start = date(year_3_end.year - 1, year_3_end.month, 1)
        year_1.period_start = year_1_start.isoformat()
        year_1.period_end = year_1_end.isoformat()
        year_2.period_start = year_2_start.isoformat()
        year_2.period_end = year_2_end.isoformat()
        year_3.period_start = year_3_start.isoformat()
        year_3.period_end = year_3_end.isoformat()
    except (TypeError, ValueError):
        pass
    operating_history = OperatingHistory(
        year_1=year_1,
        year_2=year_2,
        year_3=year_3,
        underwritten=underwritten,
    )

    inputs = draft.financing_inputs
    tier = str(inputs.get("tier", "Tier 2"))
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
    purchase_price = int(inputs.get("purchase_price", appraised_value))
    underwriting_value = min(appraised_value, purchase_price)
    ncf = underwritten.ncf

    dscr_amount = dscr_constrained_amount(
        ncf,
        tier_constraints["min_dscr"],
        underwriting_rate,
        amortization_months,
    )
    ltv_amount = ltv_constrained_amount(
        underwriting_value,
        tier_constraints["max_ltv"],
    )
    loan_amount = min(dscr_amount, ltv_amount)
    binding = "DSCR" if dscr_amount <= ltv_amount else "LTV"

    ads_note = annual_debt_service(
        loan_amount,
        note_rate,
        amortization_months,
    )
    ads_underwriting = annual_debt_service(
        loan_amount,
        underwriting_rate,
        amortization_months,
    )
    underwritten_dscr = ncf / ads_underwriting if ads_underwriting else 0.0
    actual_dscr = ncf / ads_note if ads_note else 0.0
    total_units = draft.property_physical.total_units
    gpr = underwritten.gpr
    total_opex = underwritten.total_operating_expenses
    breakeven = (total_opex + ads_note) / gpr * 100 if gpr else 0.0

    sources_uses = balance_sources_uses(
        loan_amount,
        purchase_price,
        int(inputs.get("closing_costs", round(purchase_price * 0.02))),
        underwritten.replacement_reserves,
        int(inputs.get("borrower_cash", 0)),
    )

    financing = Financing(
        loan_purpose=str(inputs.get("loan_purpose", "Acquisition")),
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
        purchase_price=purchase_price,
        purchase_date=inputs.get("purchase_date"),
        underwriting_value=underwriting_value,
        appraised_value=appraised_value,
        tier_minimum_dscr=tier_constraints["min_dscr"],
        tier_maximum_ltv=tier_constraints["max_ltv"],
        binding_constraint=binding,
        annual_debt_service_note=ads_note,
        annual_debt_service_underwriting=ads_underwriting,
        underwritten_dscr=round(underwritten_dscr, 2),
        actual_dscr=round(actual_dscr, 2),
        ltv_underwriting_value=round(loan_amount / underwriting_value * 100, 2) if underwriting_value else 0,
        ltv_appraised_value=round(loan_amount / appraised_value * 100, 2) if appraised_value else 0,
        debt_yield=round(ncf / loan_amount * 100, 2) if loan_amount else 0,
        breakeven_occupancy=round(breakeven, 2),
        dscr_constrained_amount=dscr_amount,
        ltv_constrained_amount=ltv_amount,
        sources_uses=sources_uses,
    )

    historical_t12 = {}
    for label, column in (
        ("Year 1", year_1),
        ("Year 2", year_2),
        ("Year 3", year_3),
    ):
        historical_t12[label] = HistoricalYear(
            rental_income=column.gpr + column.loss_gain_to_lease,
            other_income=(
                column.laundry_vending
                + column.parking
                + column.commercial
                + column.other_income
            ),
            vacancy_loss=-(
                column.vacancy
                + column.concessions
                + column.bad_debt
                + column.non_revenue_units
            ),
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
    data["financial_data"]["historical_t12"] = historical_t12

    return CrosswalkData.model_validate(data)
