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
    CHART_OF_ACCOUNTS,
    allocate_monthly,
    largest_remainder,
)
from lambdas.shared.models import CrosswalkData

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


def generate_t12(crosswalk: CrosswalkData, year_key: str, year_label: str) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = f"T-12 {year_label}"

    prop = crosswalk.property_identification
    fin = crosswalk.financial_data

    ws.merge_cells("A1:R1")
    ws["A1"] = f"Trailing 12-Month Operating Statement — {prop.property_name}"
    ws["A1"].font = Font(name="Calibri", size=14, bold=True)
    ws.merge_cells("A2:R2")
    ws["A2"] = year_label
    ws["A2"].font = Font(name="Calibri", size=11, italic=True)

    year_index = {"Year 1": 1, "Year 2": 2, "Year 3": 3}.get(year_key, 1)
    try:
        effective = date.fromisoformat(fin.effective_date)
        period_end = effective.replace(day=1) - timedelta(days=1)
        period_end = period_end.replace(year=period_end.year - (year_index - 1))
    except ValueError:
        period_end = date(2026, 2, 10)
        period_end = period_end.replace(year=period_end.year - (year_index - 1))

    months = []
    cursor = period_end
    for _ in range(12):
        months.append(cursor.strftime("%b-%y"))
        cursor = (cursor.replace(day=1) - timedelta(days=1))
    months = list(reversed(months))

    headers = ["Account"] + months + ["Annual Total", "Per Unit", "% of EGI"]
    for col, header in enumerate(headers, 1):
        ws.cell(row=4, column=col, value=header)
    style_header_row(ws, 4, len(headers))

    operating = None
    if crosswalk.operating_history is not None:
        operating = getattr(crosswalk.operating_history, year_key.lower().replace(" ", "_"), None)

    if operating is not None:
        category_values = {
            field: getattr(operating, field)
            for field, _ in EXPENSE_CATEGORIES
        }
        gpr = operating.gpr
        loss_gain = operating.loss_gain_to_lease
        vacancy = operating.vacancy
        concessions = operating.concessions
        bad_debt = operating.bad_debt
        non_revenue = operating.non_revenue_units
        other_income = (
            operating.laundry_vending
            + operating.parking
            + operating.commercial
            + operating.other_income
        )
        replacement_reserves = operating.replacement_reserves
    else:
        hist = fin.historical_t12.get(year_key)
        if hist is None:
            hist = fin.historical_t12.get(year_key.lower().replace(" ", "_"))
        if hist is not None:
            gpr = hist.rental_income
            loss_gain = 0
            vacancy = abs(hist.vacancy_loss)
            concessions = 0
            bad_debt = 0
            non_revenue = 0
            other_income = hist.other_income
            replacement_reserves = fin.pro_forma_expenses.replacement_reserves
            category_values = {
                field: getattr(fin.pro_forma_expenses, "real_estate_taxes" if field == "real_estate_taxes" else field, 0)
                for field, _ in EXPENSE_CATEGORIES
            }
        else:
            gpr = 0
            loss_gain = 0
            vacancy = concessions = bad_debt = non_revenue = 0
            other_income = 0
            replacement_reserves = 0
            category_values = {field: 0 for field, _ in EXPENSE_CATEGORIES}

    seed = f"{crosswalk.job_id}:{year_key}"
    state = prop.state
    total_units = phys = crosswalk.property_physical.total_units

    row = 5
    ws.cell(row=row, column=1, value="INCOME")
    ws.cell(row=row, column=1).font = Font(bold=True)
    row += 1

    category_detail_rows = []

    def write_category(category: str, label: str, annual: int) -> list[int]:
        nonlocal row
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=1).font = Font(bold=True)
        category_row = row
        row += 1
        accounts = [a for a in CHART_OF_ACCOUNTS if a[2] == category]
        weights = [a[4] for a in accounts]
        allocations = largest_remainder(annual, weights)
        detail_rows = []
        for account, allocation in zip(accounts, allocations):
            number, name, _, profile, _ = account
            ws.cell(row=row, column=1, value=f"{number} {name}")
            monthly = allocate_monthly(allocation, profile, f"{seed}:{number}", state)
            for col, val in enumerate(monthly, 2):
                ws.cell(row=row, column=col, value=val).number_format = CURRENCY_FMT
            ws.cell(row=row, column=14, value=allocation).number_format = CURRENCY_FMT
            ws.cell(row=row, column=15, value=f"={get_column_letter(14)}{row}/{total_units}").number_format = CURRENCY_FMT
            ws.cell(row=row, column=16, value=0).number_format = PCT_FMT
            detail_rows.append(row)
            row += 1
        if detail_rows:
            start = detail_rows[0]
            end = detail_rows[-1]
            for col in range(2, 15):
                letter = get_column_letter(col)
                ws.cell(category_row, col, f"=SUM({letter}{start}:{letter}{end})").number_format = CURRENCY_FMT
            ws.cell(category_row, 14, f"=SUM(N{start}:N{end})").number_format = CURRENCY_FMT
            ws.cell(category_row, 15, f"=N{category_row}/{total_units}").number_format = CURRENCY_FMT
        category_detail_rows.append(detail_rows)
        return detail_rows

    gpr_rows = write_category("gpr", "Gross Potential Rent", gpr)
    write_category("loss_gain_to_lease", "Loss/Gain to Lease", loss_gain)
    vacancy_rows = write_category("vacancy", "Less: Vacancy", -vacancy)
    write_category("concessions", "Less: Concessions", -concessions)
    write_category("bad_debt", "Less: Bad Debt", -bad_debt)
    write_category("non_revenue_units", "Less: Non-Revenue Units", -non_revenue)

    nri_row = row
    ws.cell(row=row, column=1, value="NET RENTAL INCOME")
    formula_cols = [col for col in range(2, 15)]
    formulas = []
    for col in range(2, 15):
        letter = get_column_letter(col)
        components = [f"{letter}{r}" for r in gpr_rows]
        if components:
            formula = "=" + "+".join(components)
        else:
            formula = "=0"
        ws.cell(row=row, column=col, value=formula).number_format = CURRENCY_FMT
    ws.cell(row=row, column=14, value=f"=N{row - 1}") if row else None
    row += 1

    ws.cell(row=row, column=1, value="OTHER INCOME")
    ws.cell(row=row, column=1).font = Font(bold=True)
    row += 1
    other_category_names = [
        ("laundry_vending", "Laundry / Vending"),
        ("parking", "Parking"),
        ("commercial", "Commercial Income"),
        ("other_income", "Other Income"),
    ]
    other_detail_rows = []
    remaining_other = other_income
    weights = [1, 1, 1, 1]
    allocations = largest_remainder(remaining_other, weights)
    for (category, label), allocation in zip(other_category_names, allocations):
        other_detail_rows.extend(write_category(category, label, allocation))

    egi_row = row
    ws.cell(row=row, column=1, value="EFFECTIVE GROSS INCOME")
    for col in range(2, 15):
        letter = get_column_letter(col)
        ws.cell(row=row, column=col, value=f"={letter}{nri_row}+SUM({letter}{egi_row - len(other_detail_rows)}:{letter}{egi_row - 1})").number_format = CURRENCY_FMT
    ws.cell(row=row, column=14, value=f"=SUM(N{row - len(other_detail_rows)}:N{row - 1})+N{nri_row}").number_format = CURRENCY_FMT
    row += 1

    ws.cell(row=row, column=1, value="OPERATING EXPENSES")
    ws.cell(row=row, column=1).font = Font(bold=True)
    row += 1
    expense_detail_rows = []
    for category, label in EXPENSE_CATEGORIES:
        annual = category_values.get(category, 0)
        expense_detail_rows.extend(write_category(category, label, annual))

    total_expense_row = row
    ws.cell(row=row, column=1, value="TOTAL OPERATING EXPENSES")
    if expense_detail_rows:
        for col in range(2, 15):
            letter = get_column_letter(col)
            ws.cell(row=row, column=col, value=f"=SUM({letter}{expense_detail_rows[0]}:{letter}{expense_detail_rows[-1]})").number_format = CURRENCY_FMT
    ws.cell(row=row, column=14, value=f"=SUM(N{expense_detail_rows[0]}:N{expense_detail_rows[-1]})").number_format = CURRENCY_FMT if expense_detail_rows else None
    row += 1

    noi_row = row
    ws.cell(row=row, column=1, value="NET OPERATING INCOME")
    for col in range(2, 15):
        letter = get_column_letter(col)
        ws.cell(row=row, column=col, value=f"={letter}{egi_row}-{letter}{total_expense_row}").number_format = CURRENCY_FMT
    ws.cell(row=row, column=14, value=f"=N{egi_row}-N{total_expense_row}").number_format = CURRENCY_FMT
    row += 1

    reserve_row = row
    ws.cell(row=row, column=1, value="LESS: REPLACEMENT RESERVES")
    monthly_reserve = allocate_monthly(replacement_reserves, "level", f"{seed}:reserve", state)
    for col, val in enumerate(monthly_reserve, 2):
        ws.cell(row=row, column=col, value=val).number_format = CURRENCY_FMT
    ws.cell(row=row, column=14, value=replacement_reserves).number_format = CURRENCY_FMT
    ws.cell(row=row, column=15, value=f"=N{reserve_row}/{total_units}").number_format = CURRENCY_FMT
    row += 1

    ncf_row = row
    ws.cell(row=row, column=1, value="NET CASH FLOW")
    for col in range(2, 15):
        letter = get_column_letter(col)
        ws.cell(row=row, column=col, value=f"={letter}{noi_row}-{letter}{reserve_row}").number_format = CURRENCY_FMT
    ws.cell(row=row, column=14, value=f"=N{noi_row}-N{reserve_row}").number_format = CURRENCY_FMT

    ws.column_dimensions["A"].width = 34
    for col in range(2, 17):
        ws.column_dimensions[get_column_letter(col)].width = 12

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
