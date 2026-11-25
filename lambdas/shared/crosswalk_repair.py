"""Deterministic repair of LLM-produced crosswalk drafts.

The model chooses realistic *inputs*; this module recomputes every derived
figure and maps common field-name variations onto the CrosswalkDraft contract,
so arithmetic drift or alias drift never fails Pydantic validation.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from pydantic import ValidationError

from lambdas.shared.models import OperatingColumn, Sponsorship

DEDUCTION_FIELDS = ("vacancy", "concessions", "bad_debt", "non_revenue_units")

OPERATING_ALIASES = {
    "potential_gross_rental_income": "gpr",
    "gross_potential_rent": "gpr",
    "loss_to_lease": "loss_gain_to_lease",
    "vacancy_loss": "vacancy",
    "physical_vacancy": "vacancy",
    "laundry": "laundry_vending",
    "parking_income": "parking",
    "commercial_income": "commercial",
    "payroll": "payroll_benefits",
    "administrative": "general_administrative",
    "general_and_administrative": "general_administrative",
    "management_fee_amount": "management_fee",
    "management": "management_fee",
    "water_and_sewer": "water_sewer",
    "repairs_and_maintenance": "repairs_maintenance",
    "advertising_marketing": "marketing",
    "other": "other_expenses",
}


def _int(value, default: int = 0) -> int:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _repair_identification(data: dict, user_input: dict) -> None:
    pid = data.setdefault("property_identification", {})
    pid["property_name"] = user_input.get("property_name") or pid.get("property_name") or "Subject Apartments"
    pid["address"] = user_input.get("address") or pid.get("address", "")
    pid["city"] = user_input.get("city") or pid.get("city", "")
    pid["state"] = str(user_input.get("state") or pid.get("state", "XX"))[:2].upper()
    zip_code = str(pid.get("zip", ""))
    if not re.fullmatch(r"\d{5}(-\d{4})?", zip_code):
        pid["zip"] = "00000"
    year_built = _int(user_input.get("year_built") or pid.get("year_built"), 2000)
    pid["year_built"] = min(max(year_built, 1900), 2030)
    pid["effective_age"] = min(max(_int(pid.get("effective_age"), date.today().year - year_built), 0), 130)
    pid.setdefault("county", f"{pid['city']} County")
    pid.setdefault("legal_description", "See title commitment")
    pid.setdefault("current_owner", "Subject Owner LLC")
    if not isinstance(pid.get("tax_parcel_numbers"), list) or not pid["tax_parcel_numbers"]:
        pid["tax_parcel_numbers"] = ["000-000-000"]


def _repair_physical(data: dict, user_input: dict) -> None:
    phys = data.setdefault("property_physical", {})
    total_units = _int(user_input.get("units") or phys.get("total_units"), 100)
    mix = [row for row in phys.get("unit_mix", []) if isinstance(row, dict)] or [
        {"unit_type": "1BR/1BA", "count": total_units, "avg_size_sf": 750, "bedrooms": 1, "bathrooms": 1}
    ]
    for row in mix:
        row["count"] = max(1, _int(row.get("count"), 1))
        row["avg_size_sf"] = max(1, _int(row.get("avg_size_sf"), 800))
        row["bedrooms"] = max(0, _int(row.get("bedrooms"), 1))
        row["bathrooms"] = max(1, _int(row.get("bathrooms"), 1))
    difference = total_units - sum(row["count"] for row in mix)
    largest = max(mix, key=lambda r: r["count"])
    largest["count"] = max(1, largest["count"] + difference)
    if sum(row["count"] for row in mix) != total_units:
        mix = [largest]
        largest["count"] = total_units
    for row in mix:
        row["total_sf"] = row["count"] * row["avg_size_sf"]
    phys["unit_mix"] = mix
    phys["total_units"] = total_units
    phys["building_type"] = user_input.get("property_type") or phys.get("building_type", "garden-style")
    phys["total_buildings"] = max(1, _int(phys.get("total_buildings"), 1))
    phys["stories"] = min(max(1, _int(phys.get("stories"), 3)), 100)
    net_sf = sum(row["total_sf"] for row in mix)
    phys["gross_building_area_sf"] = max(_int(phys.get("gross_building_area_sf")), round(net_sf * 1.12))
    acres = _float(phys.get("site_area_acres"), 0) or round(total_units / 20, 2)
    phys["site_area_acres"] = acres
    phys["site_area_sf"] = round(acres * 43560)
    phys["parking_spaces"] = max(0, _int(phys.get("parking_spaces"), round(total_units * 1.5)))
    phys["parking_ratio"] = round(phys["parking_spaces"] / total_units, 2)
    if not isinstance(phys.get("amenities"), list):
        phys["amenities"] = []


def _repair_market(data: dict) -> None:
    market = data.setdefault("market_data", {})
    market["submarket_vacancy_rate"] = min(max(_float(market.get("submarket_vacancy_rate"), 5.0), 0), 100)
    market["submarket_rent_growth_yoy"] = _float(market.get("submarket_rent_growth_yoy"), 3.0)
    market.setdefault("submarket", "Primary Submarket")
    for comp in market.get("comparable_properties", []):
        comp["occupancy"] = min(max(_float(comp.get("occupancy"), 94.0), 0), 100)
        comp["units"] = max(1, _int(comp.get("units"), 100))
        comp["year_built"] = min(max(_int(comp.get("year_built"), 2000), 1900), 2030)
        comp["avg_rent_per_unit"] = max(1.0, _float(comp.get("avg_rent_per_unit"), 1500))
    for sale in market.get("comparable_sales", []):
        sale["units"] = max(1, _int(sale.get("units"), 100))
        sale["sale_price"] = max(1, _int(sale.get("sale_price"), 10_000_000))
        sale["price_per_unit"] = round(sale["sale_price"] / sale["units"])
        sale["cap_rate"] = min(max(_float(sale.get("cap_rate"), 5.5), 0.5), 100)
        sale["noi"] = max(1, round(sale["sale_price"] * sale["cap_rate"] / 100))


def _repair_financials(data: dict, effective_date: str) -> None:
    fin = data.setdefault("financial_data", {})
    phys = data["property_physical"]
    units = phys["total_units"]
    fin["effective_date"] = effective_date

    occupancy = fin.setdefault("occupancy", {})
    pct = min(max(_float(occupancy.get("physical_percent"), 94.0), 60.0), 100.0)
    occupied = min(units, round(units * pct / 100))
    occupancy.update(
        physical_percent=round(occupied / units * 100, 1),
        occupied_units=occupied,
        vacant_units=units - occupied,
    )

    market_rents = fin.get("market_rents_monthly") or {}
    in_place = fin.get("in_place_rents_monthly") or {}
    fallback_rent = round(sum(_int(v) for v in market_rents.values()) / len(market_rents)) if market_rents else 1500
    for row in phys["unit_mix"]:
        t = row["unit_type"]
        market_rents[t] = max(1, _int(market_rents.get(t), fallback_rent))
        in_place[t] = max(1, _int(in_place.get(t), round(market_rents[t] * 0.97)))
    fin["market_rents_monthly"] = {row["unit_type"]: market_rents[row["unit_type"]] for row in phys["unit_mix"]}
    fin["in_place_rents_monthly"] = {row["unit_type"]: in_place[row["unit_type"]] for row in phys["unit_mix"]}

    income = fin.setdefault("pro_forma_income", {})
    pgri = sum(fin["market_rents_monthly"][row["unit_type"]] * row["count"] * 12 for row in phys["unit_mix"])
    other = max(0, _int(income.get("other_income"), round(pgri * 0.03)))
    vac_pct = min(max(_float(income.get("vacancy_collection_loss_percent"), 6.0), 3.0), 30.0)
    pgi = pgri + other
    vac_amount = round(pgi * vac_pct / 100)
    income.update(
        potential_gross_rental_income=pgri,
        other_income=other,
        potential_gross_income=pgi,
        vacancy_collection_loss_percent=vac_pct,
        vacancy_collection_loss_amount=vac_amount,
        effective_gross_income=pgi - vac_amount,
    )
    egi = income["effective_gross_income"]

    expenses = fin.setdefault("pro_forma_expenses", {})
    defaults = {
        "real_estate_taxes": 0.12, "insurance": 0.04, "utilities": 0.05,
        "repairs_maintenance": 0.05, "payroll": 0.10, "marketing": 0.01,
        "administrative": 0.02,
    }
    for key, share in defaults.items():
        expenses[key] = max(0, _int(expenses.get(key), round(egi * share)))
    mgmt_pct = min(max(_float(expenses.get("management_fee_percent"), 3.5), 2.0), 8.0)
    expenses["management_fee_percent"] = mgmt_pct
    expenses["management_fee_amount"] = round(egi * mgmt_pct / 100)
    expenses["replacement_reserves"] = max(_int(expenses.get("replacement_reserves")), 250 * units)

    variable_keys = list(defaults)
    total = sum(expenses[k] for k in variable_keys) + expenses["management_fee_amount"] + expenses["replacement_reserves"]
    ceiling = round(egi * 0.55)
    if total > ceiling:
        fixed = expenses["management_fee_amount"] + expenses["replacement_reserves"]
        scale = max(0.1, (ceiling - fixed) / max(1, total - fixed))
        for key in variable_keys:
            expenses[key] = round(expenses[key] * scale)
        total = sum(expenses[k] for k in variable_keys) + fixed
    expenses["total_operating_expenses"] = total
    expenses["expense_per_unit"] = round(total / units)
    fin["net_operating_income"] = egi - total
    fin["historical_t12"] = {}


def _repair_valuation(data: dict, effective_date: str) -> None:
    val = data.setdefault("valuation", {})
    phys = data["property_physical"]
    units = phys["total_units"]
    gba = phys["gross_building_area_sf"]
    noi = data["financial_data"]["net_operating_income"]

    income = val.setdefault("income_approach", {})
    cap = min(max(_float(income.get("cap_rate"), 5.5), 3.0), 12.0)
    income_value = round(noi / (cap / 100))
    income.update(stabilized_noi=noi, cap_rate=cap, indicated_value=income_value)

    sales = val.setdefault("sales_comparison_approach", {})
    sales_value = _int(sales.get("indicated_value"), income_value)
    if not 0.8 * income_value <= sales_value <= 1.2 * income_value:
        sales_value = round(income_value * 1.02, -4)
    sales.update(
        indicated_value=sales_value,
        value_per_unit=round(sales_value / units),
        value_per_sf=round(sales_value / gba, 2),
    )

    final = val.setdefault("final_value_conclusion", {})
    market_value = _int(final.get("market_value"), income_value)
    if not 0.9 * income_value <= market_value <= 1.1 * income_value:
        market_value = round(income_value, -4)
    final.update(
        market_value=market_value,
        value_per_unit=round(market_value / units),
        value_per_sf=round(market_value / gba, 2),
        effective_date=effective_date,
    )


def _repair_operating_year1(data: dict) -> None:
    raw = data.get("operating_year1")
    if not isinstance(raw, dict):
        data["operating_year1"] = None
        return
    mapped = {}
    for key, value in raw.items():
        mapped[OPERATING_ALIASES.get(key, key)] = value
    column = {}
    for field in OperatingColumn.model_fields:
        if field in ("period_start", "period_end"):
            continue
        amount = _int(mapped.get(field), 0)
        if field in DEDUCTION_FIELDS:
            amount = abs(amount)
        elif field != "loss_gain_to_lease":
            amount = max(0, amount)
        column[field] = amount
    try:
        candidate = OperatingColumn.model_validate(column)
    except ValidationError:
        data["operating_year1"] = None
        return
    pro_forma_egi = data["financial_data"]["pro_forma_income"]["effective_gross_income"]
    within_band = 0.85 * pro_forma_egi <= candidate.effective_gross_income <= 1.10 * pro_forma_egi
    expense_ratio = candidate.total_operating_expenses / max(1, candidate.effective_gross_income)
    data["operating_year1"] = column if within_band and 0.2 <= expense_ratio <= 0.65 else None


def _repair_financing_inputs(data: dict) -> None:
    inputs = data.get("financing_inputs") if isinstance(data.get("financing_inputs"), dict) else {}
    tier = str(inputs.get("tier", "Tier 2")).title()
    inputs["tier"] = tier if tier in ("Tier 2", "Tier 3", "Tier 4") else "Tier 2"
    purpose = str(inputs.get("loan_purpose", "Acquisition"))
    inputs["loan_purpose"] = "Refinance" if "refi" in purpose.lower() else "Acquisition"
    inputs["note_rate"] = round(min(max(_float(inputs.get("note_rate"), 6.0), 4.5), 8.5), 2)
    term = _int(inputs.get("term_months"), 120)
    inputs["term_months"] = min((60, 84, 120, 144, 180), key=lambda t: abs(t - term))
    inputs["amortization_months"] = 360
    inputs["interest_only_months"] = min(max(_int(inputs.get("interest_only_months"), 0), 0), inputs["term_months"])
    inputs["execution"] = "DUS"
    inputs["product"] = "Conventional Fixed"
    inputs.setdefault("prepayment_terms", "Yield maintenance through the final 6 months of the term")
    market_value = data["valuation"]["final_value_conclusion"]["market_value"]
    price = _int(inputs.get("purchase_price"), market_value)
    if not 0.85 * market_value <= price <= 1.05 * market_value:
        price = round(market_value * 0.98, -4)
    inputs["purchase_price"] = price
    effective = date.fromisoformat(data["financial_data"]["effective_date"])
    inputs["purchase_date"] = (effective + timedelta(days=45)).isoformat()
    inputs.pop("closing_costs", None)
    inputs.pop("borrower_cash", None)
    data["financing_inputs"] = inputs


def _default_sponsorship(data: dict, job_id: str) -> dict:
    name = data["property_identification"]["property_name"]
    market_value = data["valuation"]["final_value_conclusion"]["market_value"]
    base = name.replace("Apartments", "").replace("Test", "").strip() or "Summit"
    first = base.split()[0]
    return {
        "borrower_name": f"{first} Residential Owner LLC",
        "borrower_type": "Single-asset Delaware limited liability company",
        "key_principals": [
            {"name": "Daniel R. Whitaker", "role": "Managing Member", "years_experience": 22,
             "units_owned": 4800, "net_worth": round(market_value * 0.6, -5),
             "liquidity": round(market_value * 0.06, -4)},
            {"name": "Elena M. Ortiz", "role": "Principal, Asset Management", "years_experience": 15,
             "units_owned": 2100, "net_worth": round(market_value * 0.25, -5),
             "liquidity": round(market_value * 0.02, -4)},
        ],
        "guarantor": "Daniel R. Whitaker",
        "property_management": {
            "name": f"{first} Residential Management, Inc.",
            "management_fee_percent": data["financial_data"]["pro_forma_expenses"]["management_fee_percent"],
            "on_site_staffing": "Community manager, assistant manager, two leasing agents, and three maintenance technicians",
        },
    }


def _repair_sponsorship(data: dict, job_id: str) -> None:
    raw = data.get("sponsorship")
    default = _default_sponsorship(data, job_id)
    if not isinstance(raw, dict):
        data["sponsorship"] = default
        return
    market_value = data["valuation"]["final_value_conclusion"]["market_value"]
    principals = []
    for p in raw.get("key_principals") or []:
        if not isinstance(p, dict) or not p.get("name"):
            continue
        principals.append({
            "name": p["name"],
            "role": p.get("role") or p.get("title") or "Principal",
            "years_experience": max(0, _int(p.get("years_experience", p.get("experience_years")), 12)),
            "units_owned": max(0, _int(p.get("units_owned", p.get("owned_units")), 1500)),
            "net_worth": max(0, _int(p.get("net_worth"), 0)) or round(market_value * 0.4, -5),
            "liquidity": max(0, _int(p.get("liquidity"), 0)) or round(market_value * 0.04, -4),
        })
    mgmt = raw.get("property_management") if isinstance(raw.get("property_management"), dict) else {}
    repaired = {
        "borrower_name": raw.get("borrower_name") or default["borrower_name"],
        "borrower_type": raw.get("borrower_type") or default["borrower_type"],
        "key_principals": principals or default["key_principals"],
        "guarantor": raw.get("guarantor") or (principals[0]["name"] if principals else default["guarantor"]),
        "property_management": {
            "name": mgmt.get("name") or mgmt.get("company_name") or mgmt.get("company") or default["property_management"]["name"],
            "management_fee_percent": min(max(_float(mgmt.get("management_fee_percent", mgmt.get("fee_percent")),
                                                     default["property_management"]["management_fee_percent"]), 0), 100),
            "on_site_staffing": mgmt.get("on_site_staffing") or mgmt.get("staffing") or default["property_management"]["on_site_staffing"],
        },
    }
    try:
        Sponsorship.model_validate(repaired)
        data["sponsorship"] = repaired
    except ValidationError:
        data["sponsorship"] = default


def _repair_third_party(data: dict, job_id: str) -> None:
    raw = data.get("third_party_reports") if isinstance(data.get("third_party_reports"), dict) else {}
    effective = date.fromisoformat(data["financial_data"]["effective_date"])
    units = data["property_physical"]["total_units"]
    age = data["property_identification"]["effective_age"]

    def pick(section_keys, field_keys, default):
        for sk in section_keys:
            section = raw.get(sk)
            if isinstance(section, dict):
                for fk in field_keys:
                    if section.get(fk):
                        return section[fk]
        return default

    immediate = _int(pick(["property_condition_assessment", "property_condition"],
                          ["immediate_repairs", "deferred_maintenance"], units * 350), units * 350)
    seismic = raw.get("seismic") if isinstance(raw.get("seismic"), dict) else {}
    zoning = raw.get("zoning") if isinstance(raw.get("zoning"), dict) else {}
    data["third_party_reports"] = {
        "appraisal": {
            "firm": str(pick(["appraisal"], ["firm", "appraiser_name", "appraiser"], "Meridian Valuation Advisors")),
            "date": (effective - timedelta(days=5)).isoformat(),
            "value": data["valuation"]["final_value_conclusion"]["market_value"],
        },
        "property_condition_assessment": {
            "firm": str(pick(["property_condition_assessment", "property_condition"], ["firm", "inspector"], "Keystone Building Sciences")),
            "date": (effective - timedelta(days=12)).isoformat(),
            "immediate_repairs": max(0, immediate),
            "twelve_year_reserve_need": units * (2600 + 60 * min(age, 40)),
        },
        "environmental_site_assessment": {
            "firm": str(pick(["environmental_site_assessment", "environmental"], ["firm", "phase_1_provider"], "Clearwater Environmental Group")),
            "date": (effective - timedelta(days=12)).isoformat(),
            "finding": str(pick(["environmental_site_assessment", "environmental"], ["finding", "findings"],
                                "Phase I ESA identified no Recognized Environmental Conditions; no Phase II recommended.")),
        },
        "seismic_applicable": bool(raw.get("seismic_applicable", seismic.get("required", False))),
        "seismic_pml": None,
        "zoning_status": str(raw.get("zoning_status") or zoning.get("status") or "Legal conforming"),
    }


def repair_draft(raw: dict, user_input: dict, job_id: str, today: date | None = None) -> dict:
    """Return a CrosswalkDraft-compatible dict with all derived figures recomputed."""
    data = dict(raw)
    data["job_id"] = job_id
    data.pop("generated_at", None)
    effective_date = (today or date.today()).isoformat()

    _repair_identification(data, user_input)
    _repair_physical(data, user_input)
    _repair_market(data)
    _repair_financials(data, effective_date)
    _repair_valuation(data, effective_date)
    _repair_operating_year1(data)
    _repair_financing_inputs(data)
    _repair_sponsorship(data, job_id)
    _repair_third_party(data, job_id)
    if not isinstance(data.get("history_assumptions"), dict):
        data["history_assumptions"] = {}
    return data
