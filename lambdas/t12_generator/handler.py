"""T-12 and Rent Roll Generator Lambda — creates detailed Excel workbooks."""

from __future__ import annotations

import hashlib
import io
import logging
import random
from datetime import date, timedelta

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from lambdas.shared import s3_utils
from lambdas.shared.chart_of_accounts import (
    allocate_monthly,
    applicable_accounts,
    largest_remainder,
)
from lambdas.shared.models import CrosswalkData, OperatingColumn

logger = logging.getLogger(__name__)

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael",
    "Linda", "David", "Elizabeth", "William", "Barbara", "Richard", "Susan",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
]

HEADER_FILL = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
DATA_FONT = Font(name="Calibri", size=11)
CURRENCY_FMT = "#,##0"
PCT_FMT = "0.0%"
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)

EXPENSE_CATEGORIES = [
    ("real_estate_taxes", "REAL ESTATE TAXES"),
    ("insurance", "INSURANCE"),
    ("utilities", "UTILITIES"),
    ("water_sewer", "WATER & SEWER"),
    ("repairs_maintenance", "REPAIRS & MAINTENANCE"),
    ("payroll_benefits", "PAYROLL & BENEFITS"),
    ("general_administrative", "GENERAL & ADMINISTRATIVE"),
    ("marketing", "ADVERTISING & MARKETING"),
    ("professional_fees", "PROFESSIONAL FEES"),
    ("management_fee", "MANAGEMENT FEES"),
    ("ground_rent", "GROUND RENT"),
    ("other_expenses", "OTHER EXPENSES"),
]


def style_header_row(ws, row: int, col_count: int) -> None:
    for col in range(1, col_count + 1):
        cell = ws.cell(row=row, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
        cell.border = THIN_BORDER


def generate_rent_roll(crosswalk: CrosswalkData) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Rent Roll"

    prop = crosswalk.property_identification
    fin = crosswalk.financial_data
    phys = crosswalk.property_physical

    effective_text = fin.effective_date
    try:
        effective = date.fromisoformat(effective_text)
    except ValueError:
        effective = date(2026, 2, 10)

    ws.merge_cells("A1:N1")
    ws["A1"] = f"Rent Roll — {prop.property_name}"
    ws["A1"].font = Font(name="Calibri", size=14, bold=True)
    ws.merge_cells("A2:N2")
    ws["A2"] = f"As of {effective_text}"
    ws["A2"].font = Font(name="Calibri", size=11, italic=True)

    headers = [
        "Unit #", "Unit Type", "SF", "Tenant Name", "Move-In",
        "Lease Start", "Lease End", "Market Rent", "In-Place Rent",
        "Concession", "Security Deposit", "Balance Due", "Status",
    ]
    for col, header in enumerate(headers, 1):
        ws.cell(row=4, column=col, value=header)
    style_header_row(ws, 4, len(headers))

    rng = random.Random(
        int.from_bytes(
            hashlib.sha256(
                f"{crosswalk.job_id}:rent-roll".encode("utf-8")
            ).digest()[:8],
            "big",
        )
    )
    occupied_indices = set(
        rng.sample(
            range(phys.total_units),
            k=min(fin.occupancy.occupied_units, phys.total_units),
        )
    )

    unit_rows = []
    unit_num = 100
    total_generated = 0
    for unit_item in phys.unit_mix:
        market_rent = fin.market_rents_monthly.get(unit_item.unit_type, 1400)
        in_place_rent = fin.in_place_rents_monthly.get(unit_item.unit_type, market_rent)
        jitter = rng.sample(
            list(range(-25, 26)),
            k=max(1, unit_item.count),
        ) if unit_item.count <= 51 else [
            rng.randint(-25, 25) for _ in range(unit_item.count)
        ]
        jitter_values = (jitter + [0] * unit_item.count)[:unit_item.count]
        difference = (unit_item.count - len(jitter_values))
        if difference > 0:
            jitter_values.extend([0] * difference)
        occupied_count = sum(
            1
            for i in range(total_generated, total_generated + unit_item.count)
            if i in occupied_indices
        )
        rents = [in_place_rent + jitter_values[i] for i in range(unit_item.count)]
        if occupied_count:
            per_rent_sum = in_place_rent * occupied_count
            occupied_rents = [rent for i, rent in zip(range(unit_item.count), rents) if total_generated + i in occupied_indices]
            current_sum = sum(occupied_rents)
            if occupied_rents and current_sum:
                occupied_rents[-1] += per_rent_sum - current_sum
                k = 0
                for i in range(unit_item.count):
                    if total_generated + i in occupied_indices:
                        rents[i] = occupied_rents[k]
                        k += 1

        for i in range(unit_item.count):
            is_occupied = total_generated in occupied_indices
            unit_number = f"{unit_num + i}"
            if is_occupied:
                tenant = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
                move_in = effective - timedelta(days=rng.randint(30, 365))
                lease_start = move_in
                lease_end = lease_start + timedelta(days=365)
                rent = rents[i]
                concession = max(0, market_rent - rent)
                security_deposit = round(rent)
                balance_due = 0
                status = "Occupied"
            else:
                tenant = "— Vacant —"
                move_in = None
                lease_start = None
                lease_end = None
                rent = 0
                concession = 0
                security_deposit = 0
                balance_due = 0
                status = "Vacant"

            unit_rows.append([
                unit_number, unit_item.unit_type, unit_item.avg_size_sf,
                tenant,
                move_in.isoformat() if move_in else "",
                lease_start.isoformat() if lease_start else "",
                lease_end.isoformat() if lease_end else "",
                market_rent, rent, concession, security_deposit, balance_due, status,
            ])
            total_generated += 1
        unit_num += unit_item.count + 10

    row = 5
    for values in unit_rows:
        for col, value in enumerate(values, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.border = THIN_BORDER
            cell.font = DATA_FONT
            if col in {8, 9, 10, 11, 12}:
                cell.number_format = CURRENCY_FMT
        row += 1

    row += 1
    ws[f"A{row}"] = "Unit Type Summary"
    ws[f"A{row}"].font = Font(bold=True)
    summary_headers = ["Unit Type", "Units", "Occupied", "Vacant", "Avg Market Rent", "Avg In-Place Rent"]
    for col, header in enumerate(summary_headers, 1):
        ws.cell(row=row + 1, column=col, value=header)
    style_header_row(ws, row + 1, len(summary_headers))

    summary_row = row + 2
    grand_units = grand_occupied = 0
    grand_market_total = grand_in_place_total = 0
    for unit_item in phys.unit_mix:
        matching = [values for values in unit_rows if values[1] == unit_item.unit_type]
        occupied = sum(1 for values in matching if values[12] == "Occupied")
        in_place_values = [values[8] for values in matching if values[12] == "Occupied"]
        market_average = round(sum(values[7] for values in matching) / len(matching)) if matching else 0
        in_place_average = round(sum(in_place_values) / len(in_place_values)) if in_place_values else 0
        ws.cell(summary_row, 1, unit_item.unit_type)
        ws.cell(summary_row, 2, len(matching))
        ws.cell(summary_row, 3, occupied)
        ws.cell(summary_row, 4, len(matching) - occupied)
        ws.cell(summary_row, 5, market_average).number_format = CURRENCY_FMT
        ws.cell(summary_row, 6, in_place_average).number_format = CURRENCY_FMT
        grand_units += len(matching)
        grand_occupied += occupied
        grand_market_total += market_average * len(matching)
        grand_in_place_total += in_place_average * occupied
        summary_row += 1

    ws.cell(summary_row, 1, "Grand Total")
    ws.cell(summary_row, 2, grand_units)
    ws.cell(summary_row, 3, grand_occupied)
    ws.cell(summary_row, 4, grand_units - grand_occupied)
    ws.cell(summary_row, 5, round(grand_market_total / grand_units) if grand_units else 0).number_format = CURRENCY_FMT
    ws.cell(summary_row, 6, round(grand_in_place_total / grand_occupied) if grand_occupied else 0).number_format = CURRENCY_FMT

    widths = [10, 12, 8, 22, 12, 12, 12, 14, 14, 12, 14, 12, 10]
    for i, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = width

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


RENTAL_CATEGORIES = [
    ("gpr", 1),
    ("loss_gain_to_lease", 1),
    ("vacancy", -1),
    ("concessions", -1),
    ("bad_debt", -1),
    ("non_revenue_units", -1),
]
OTHER_INCOME_CATEGORIES = ["laundry_vending", "parking", "commercial", "other_income"]
BOLD = Font(name="Calibri", size=11, bold=True)
SUBTOTAL_FILL = PatternFill(start_color="DDEBF7", end_color="DDEBF7", fill_type="solid")
TOTAL_FILL = PatternFill(start_color="BDD7EE", end_color="BDD7EE", fill_type="solid")


def _operating_column(crosswalk: CrosswalkData, year_key: str) -> OperatingColumn:
    if crosswalk.operating_history is not None:
        return getattr(crosswalk.operating_history, year_key.lower().replace(" ", "_"))
    hist = crosswalk.financial_data.historical_t12.get(year_key)
    if hist is None:
        raise ValueError(f"No operating data for {year_key}")
    return OperatingColumn(
        gpr=hist.rental_income,
        vacancy=-hist.vacancy_loss,
        other_income=hist.other_income,
        other_expenses=hist.operating_expenses,
    )


def _month_labels(column: OperatingColumn, crosswalk: CrosswalkData, year_index: int) -> list[str]:
    if column.period_start:
        start = date.fromisoformat(column.period_start)
    else:
        effective = date.fromisoformat(crosswalk.financial_data.effective_date)
        start = date(effective.year - year_index, effective.month, 1)
    labels = []
    year, month = start.year, start.month
    for _ in range(12):
        labels.append(date(year, month, 1).strftime("%b-%y"))
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return labels


def _allocate_category(
    crosswalk: CrosswalkData, category: str, annual: int, seed: str,
) -> list[tuple[str, str, list[int]]]:
    """Split a category's annual amount into GL accounts and months (exact integers)."""
    prop = crosswalk.property_identification
    phys = crosswalk.property_physical
    accounts = applicable_accounts(category, prop.state, phys.building_type)
    rng = random.Random(int.from_bytes(hashlib.sha256(f"{seed}:{category}".encode()).digest()[:8], "big"))
    weights = [max(1, round(account[4] * rng.uniform(0.85, 1.15))) for account in accounts]
    rows = []
    for (number, name, _, profile, _), amount in zip(accounts, largest_remainder(annual, weights)):
        monthly = allocate_monthly(amount, profile, f"{seed}:{number}", prop.state)
        rows.append((number, name, monthly))
    return rows


def generate_t12(crosswalk: CrosswalkData, year_key: str, year_label: str) -> bytes:
    """Generate a detailed T-12 operating statement whose subtotals are live formulas."""
    wb = Workbook()
    ws = wb.active
    ws.title = f"T-12 {year_label}"

    prop = crosswalk.property_identification
    units = crosswalk.property_physical.total_units
    year_index = {"Year 1": 1, "Year 2": 2, "Year 3": 3}.get(year_key, 1)
    column = _operating_column(crosswalk, year_key)
    months = _month_labels(column, crosswalk, year_index)
    seed = f"{crosswalk.job_id}:{year_key}"

    ws.merge_cells("A1:P1")
    ws["A1"] = f"Trailing 12-Month Operating Statement ? {prop.property_name}"
    ws["A1"].font = Font(name="Calibri", size=14, bold=True)
    ws.merge_cells("A2:P2")
    ws["A2"] = f"{year_label}: {months[0]} through {months[-1]} ? {units} units ? Synthetic data"
    ws["A2"].font = Font(name="Calibri", size=11, italic=True)

    headers = ["Account"] + months + ["Annual Total", "Per Unit", "% of EGI"]
    for col, header in enumerate(headers, 1):
        ws.cell(row=4, column=col, value=header)
    style_header_row(ws, 4, len(headers))

    row = 5
    egi_ref: dict[str, int] = {}
    percent_rows: list[int] = []

    def label_row(text: str) -> None:
        nonlocal row
        ws.cell(row=row, column=1, value=text).font = BOLD
        row += 1

    def detail_row(number: str, name: str, monthly: list[int], sign: int = 1) -> int:
        nonlocal row
        ws.cell(row=row, column=1, value=f"{number} {name}").font = DATA_FONT
        for i, amount in enumerate(monthly):
            ws.cell(row=row, column=2 + i, value=sign * amount).number_format = CURRENCY_FMT
        ws.cell(row=row, column=14, value=f"=SUM(B{row}:M{row})").number_format = CURRENCY_FMT
        ws.cell(row=row, column=15, value=f"=ROUND(N{row}/{units},0)").number_format = CURRENCY_FMT
        percent_rows.append(row)
        row += 1
        return row - 1

    def formula_row(text: str, template: str, fill=SUBTOTAL_FILL) -> int:
        """template uses {c} as the column letter placeholder."""
        nonlocal row
        ws.cell(row=row, column=1, value=text).font = BOLD
        for col in range(2, 15):
            letter = get_column_letter(col)
            cell = ws.cell(row=row, column=col, value="=" + template.format(c=letter))
            cell.number_format = CURRENCY_FMT
            cell.font = BOLD
        ws.cell(row=row, column=15, value=f"=ROUND(N{row}/{units},0)").number_format = CURRENCY_FMT
        for col in range(1, 17):
            ws.cell(row=row, column=col).fill = fill
        percent_rows.append(row)
        row += 1
        return row - 1

    # --- Revenue -----------------------------------------------------------
    label_row("REVENUE")
    rental_rows = []
    vacancy_rows = []
    gpr_row = None
    for category, sign in RENTAL_CATEGORIES:
        amount = abs(getattr(column, category)) if sign < 0 else getattr(column, category)
        for number, name, monthly in _allocate_category(crosswalk, category, amount, seed):
            r = detail_row(number, name, monthly, sign)
            rental_rows.append(r)
            if category == "gpr" and gpr_row is None:
                gpr_row = r
            if category == "vacancy":
                vacancy_rows.append(r)
    nri_row = formula_row("NET RENTAL INCOME", f"SUM({{c}}{rental_rows[0]}:{{c}}{rental_rows[-1]})")

    other_rows = []
    for category in OTHER_INCOME_CATEGORIES:
        for number, name, monthly in _allocate_category(crosswalk, category, getattr(column, category), seed):
            other_rows.append(detail_row(number, name, monthly))
    toi_row = formula_row("TOTAL OTHER INCOME", f"SUM({{c}}{other_rows[0]}:{{c}}{other_rows[-1]})")
    egi_row = formula_row("EFFECTIVE GROSS INCOME", f"{{c}}{nri_row}+{{c}}{toi_row}", TOTAL_FILL)
    egi_ref["row"] = egi_row
    row += 1

    # --- Operating expenses ------------------------------------------------
    label_row("OPERATING EXPENSES")
    category_total_rows = []
    for category, title in EXPENSE_CATEGORIES:
        detail_rows = [
            detail_row(number, name, monthly)
            for number, name, monthly in _allocate_category(crosswalk, category, getattr(column, category), seed)
        ]
        category_total_rows.append(
            formula_row(f"Total {title.title()}", f"SUM({{c}}{detail_rows[0]}:{{c}}{detail_rows[-1]})")
        )
    opex_row = formula_row(
        "TOTAL OPERATING EXPENSES",
        "+".join(f"{{c}}{r}" for r in category_total_rows),
        TOTAL_FILL,
    )
    noi_row = formula_row("NET OPERATING INCOME", f"{{c}}{egi_row}-{{c}}{opex_row}", TOTAL_FILL)
    row += 1

    # --- Below the line ----------------------------------------------------
    label_row("BELOW THE LINE (excluded from NOI)")
    reserve_monthly = allocate_monthly(column.replacement_reserves, "level", f"{seed}:6010", prop.state)
    reserve_row = detail_row("6010", "Replacement Reserve Deposits", reserve_monthly)
    formula_row("NET CASH FLOW", f"{{c}}{noi_row}-{{c}}{reserve_row}", TOTAL_FILL)
    row += 1

    # % of EGI for income/expense rows
    for r in percent_rows:
        ws.cell(row=r, column=16, value=f"=IF($N${egi_row}=0,0,N{r}/$N${egi_row})").number_format = PCT_FMT

    # --- Occupancy statistics ---------------------------------------------
    label_row("OCCUPANCY STATISTICS")
    occupied_row = row
    ws.cell(row=row, column=1, value="Occupied Units").font = DATA_FONT
    for col in range(2, 14):
        letter = get_column_letter(col)
        vacancy_sum = "+".join(f"{letter}{r}" for r in vacancy_rows) or "0"
        ws.cell(row=row, column=col,
                value=f"=ROUND({units}*(1+({vacancy_sum})/{letter}{gpr_row}),0)")
    row += 1
    ws.cell(row=row, column=1, value="Physical Occupancy %").font = DATA_FONT
    for col in range(2, 14):
        letter = get_column_letter(col)
        ws.cell(row=row, column=col, value=f"={letter}{occupied_row}/{units}").number_format = PCT_FMT
    row += 1
    ws.cell(row=row, column=1, value="Economic Occupancy %").font = DATA_FONT
    for col in range(2, 14):
        letter = get_column_letter(col)
        ws.cell(row=row, column=col, value=f"={letter}{nri_row}/{letter}{gpr_row}").number_format = PCT_FMT

    ws.column_dimensions["A"].width = 40
    for col in range(2, 17):
        ws.column_dimensions[get_column_letter(col)].width = 12
    ws.freeze_panes = "B5"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def handler(event, context):
    job_id = event["job_id"]
    logger.info("Generating T-12 and Rent Roll for job %s", job_id)

    data = s3_utils.read_json(job_id, "crosswalk-data.json")
    crosswalk = CrosswalkData.model_validate(data)

    rent_roll_bytes = generate_rent_roll(crosswalk)
    s3_utils.write_bytes(
        job_id,
        "outputs/rent_roll.xlsx",
        rent_roll_bytes,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    for year_key, year_label, output_name in [
        ("Year 1", "Year 1", "t12_year1.xlsx"),
        ("Year 2", "Year 2", "t12_year2.xlsx"),
        ("Year 3", "Year 3", "t12_year3.xlsx"),
    ]:
        t12_bytes = generate_t12(crosswalk, year_key, year_label)
        s3_utils.write_bytes(
            job_id,
            f"outputs/{output_name}",
            t12_bytes,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    return {
        "status": "success",
        "job_id": job_id,
        "files": [
            "outputs/rent_roll.xlsx",
            "outputs/t12_year1.xlsx",
            "outputs/t12_year2.xlsx",
            "outputs/t12_year3.xlsx",
        ],
    }
