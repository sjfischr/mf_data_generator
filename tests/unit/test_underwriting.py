import pytest

from lambdas.shared.models import OperatingColumn
from lambdas.shared.underwriting import (
    build_underwritten_column,
    dscr_constrained_amount,
    ltv_constrained_amount,
)


def test_dscr_example():
    amount = dscr_constrained_amount(
        ncf=1_250_000,
        minimum_dscr=1.25,
        annual_rate_percent=6.0,
        amortization_months=360,
    )
    assert amount == 13_899_000


def test_ltv_binding_amount():
    amount = ltv_constrained_amount(
        underwriting_value=25_000_000,
        maximum_ltv_percent=80.0,
    )
    assert amount == 20_000_000


def test_underwritten_floors():
    year_1 = OperatingColumn(
        gpr=1_000_000,
        vacancy=20_000,
        concessions=5_000,
        bad_debt=5_000,
        laundry_vending=100_000,
        real_estate_taxes=100_000,
        insurance=20_000,
        utilities=40_000,
        repairs_maintenance=30_000,
        payroll_benefits=50_000,
        general_administrative=20_000,
        management_fee=20_000,
        replacement_reserves=20_000,
    )

    underwritten = build_underwritten_column(year_1, total_units=200)

    assert underwritten.vacancy + underwritten.concessions + underwritten.bad_debt >= 50_000
    assert underwritten.management_fee >= underwritten.effective_gross_income * 0.03
    assert underwritten.replacement_reserves == 40_000
    assert underwritten.real_estate_taxes == 103_000
    assert underwritten.insurance == 20_000
