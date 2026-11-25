import io
import json

from openpyxl import load_workbook

from lambdas.qc_validator import handler as qc
from lambdas.t12_generator.handler import generate_rent_roll, generate_t12


def _workbook(data: bytes):
    return load_workbook(io.BytesIO(data)).active


def _detail_totals(ws) -> tuple[dict, int]:
    totals, count = {"4": 0, "5": 0, "6": 0}, 0
    for row in range(5, ws.max_row + 1):
        label = str(ws.cell(row, 1).value or "")
        if label[:4].isdigit():
            count += 1
            totals[label[0]] += sum(ws.cell(row, c).value for c in range(2, 14))
    return totals, count


def test_t12_ties_to_operating_history(finalized_crosswalk):
    cw = finalized_crosswalk
    for year in (1, 2, 3):
        ws = _workbook(generate_t12(cw, f"Year {year}", f"Year {year}"))
        totals, count = _detail_totals(ws)
        column = getattr(cw.operating_history, f"year_{year}")
        assert totals["4"] == column.effective_gross_income
        assert totals["5"] == column.total_operating_expenses
        assert totals["4"] - totals["5"] - totals["6"] == column.ncf
        assert count >= 40
    ws = _workbook(generate_t12(cw, "Year 1", "Year 1"))
    assert (ws.cell(4, 2).value, ws.cell(4, 13).value) == ("Nov-25", "Oct-26")
    labels = [str(ws.cell(r, 1).value) for r in range(5, ws.max_row + 1)]
    assert labels.index("NET OPERATING INCOME") < next(i for i, l in enumerate(labels) if l.startswith("6010"))
    assert ws.cell(labels.index("NET OPERATING INCOME") + 5, 14).value.startswith("=")


def test_t12_is_deterministic_and_climate_aware(finalized_crosswalk):
    cw = finalized_crosswalk
    assert generate_t12(cw, "Year 1", "Year 1") == generate_t12(cw, "Year 1", "Year 1")
    denver = [str(c.value) for c in _workbook(generate_t12(cw, "Year 1", "Year 1"))["A"]]
    assert any("Snow Removal" in label for label in denver)
    cw.property_identification.state = "TX"
    texas = [str(c.value) for c in _workbook(generate_t12(cw, "Year 1", "Year 1"))["A"]]
    assert not any("Snow Removal" in label for label in texas)
    assert not any("Elevator" in label for label in texas)


def test_rent_roll_ties_to_crosswalk(finalized_crosswalk):
    cw = finalized_crosswalk
    ws = _workbook(generate_rent_roll(cw))
    assert ws["A2"].value == f"As of {cw.financial_data.effective_date}"
    rows = [[ws.cell(r, c).value for c in range(1, 14)] for r in range(5, 5 + cw.property_physical.total_units)]
    assert sum(1 for r in rows if r[12] == "Occupied") == cw.financial_data.occupancy.occupied_units
    for unit_type, rent in cw.financial_data.in_place_rents_monthly.items():
        occupied = [r[8] for r in rows if r[1] == unit_type and r[12] == "Occupied"]
        assert sum(occupied) == rent * len(occupied)


def test_qc_detects_t12_mismatch(finalized_crosswalk, mocker):
    cw = finalized_crosswalk
    good = {f"outputs/t12_year{y}.xlsx": generate_t12(cw, f"Year {y}", f"Year {y}") for y in (1, 2, 3)}
    mocker.patch.object(qc, "_read_object", side_effect=lambda job, path: good[path])
    log = qc.CheckLog()
    qc.check_t12_workbooks(cw, "job", log)
    assert log.issues == [] and log.count == 18

    wb = load_workbook(io.BytesIO(good["outputs/t12_year2.xlsx"]))
    ws = wb.active
    first_expense = next(r for r in range(5, ws.max_row + 1) if str(ws.cell(r, 1).value).startswith("5"))
    ws.cell(first_expense, 2).value += 100
    buf = io.BytesIO(); wb.save(buf); good["outputs/t12_year2.xlsx"] = buf.getvalue()
    log = qc.CheckLog()
    qc.check_t12_workbooks(cw, "job", log)
    assert {i["location"] for i in log.issues} == {"t12_year2.xlsx"}
    assert any("NOI" in i["description"] for i in log.issues)
