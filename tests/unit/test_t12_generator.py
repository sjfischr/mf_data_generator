from openpyxl import load_workbook
import io

from lambdas.t12_generator.handler import generate_rent_roll, generate_t12
from lambdas.shared.chart_of_accounts import CHART_OF_ACCOUNTS
import pytest


@pytest.fixture
def sample_crosswalk_dict():
    from tests.unit.test_models import sample_crosswalk_dict as fixture
    return fixture.__pytest_wrapped__.obj()


def test_rent_roll_ties_to_crosswalk(sample_crosswalk_dict):
    from lambdas.shared.models import CrosswalkData

    crosswalk = CrosswalkData.model_validate(sample_crosswalk_dict)
    data = generate_rent_roll(crosswalk)
    wb = load_workbook(io.BytesIO(data), data_only=False)
    ws = wb["Rent Roll"]

    header = [ws.cell(4, col).value for col in range(1, 14)]
    assert "In-Place Rent" in header
    assert ws["A2"].value == f"As of {crosswalk.financial_data.effective_date}"
    assert ws.max_row >= 10


def test_t12_is_deterministic_and_detailed(sample_crosswalk_dict):
    from lambdas.shared.models import CrosswalkData

    crosswalk = CrosswalkData.model_validate(sample_crosswalk_dict)
    first = generate_t12(crosswalk, "Year 1", "Year 1")
    second = generate_t12(crosswalk, "Year 1", "Year 1")
    assert first == second

    wb = load_workbook(io.BytesIO(first), data_only=False)
    ws = wb["T-12 Year 1"]
    detail_rows = sum(
        1
        for row in range(5, ws.max_row + 1)
        if ws.cell(row, 1).value
        and any(str(ws.cell(row, 1).value).startswith(number)
                for number in [str(account[0]) for account in CHART_OF_ACCOUNTS])
    )
    assert detail_rows >= 40

