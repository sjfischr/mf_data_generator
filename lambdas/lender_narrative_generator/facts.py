"""Build the fact sheet: the only figures narrative prose may cite."""

from __future__ import annotations

from lambdas.shared.models import CrosswalkData

try:
    from lambdas.lender_narrative_generator import tables
except ImportError:  # pragma: no cover - flat Lambda bundle
    import tables  # type: ignore[no-redef]

money, pct, ratio = tables.money, tables.pct, tables.ratio


def fmt_dollar(value: float) -> str:
    return money(value)


def build_fact_sheet(cw: CrosswalkData) -> dict:
    prop, phys, fin, mkt = cw.property_identification, cw.property_physical, cw.financial_data, cw.market_data
    loan, hist, val = cw.financing, cw.operating_history, cw.valuation
    uw, y1 = hist.underwritten, hist.year_1
    sp, tpr = cw.sponsorship, cw.third_party_reports
    refi = tables.refinance_projection(cw)

    facts = {
        "property": {
            "name": prop.property_name,
            "address": f"{prop.address}, {prop.city}, {prop.state} {prop.zip}",
            "county": prop.county,
            "year_built": prop.year_built,
            "effective_age_years": prop.effective_age,
            "building_type": phys.building_type,
            "units": phys.total_units,
            "buildings": phys.total_buildings,
            "stories": phys.stories,
            "gross_building_area_sf": f"{phys.gross_building_area_sf:,}",
            "site_acres": phys.site_area_acres,
            "parking_spaces": phys.parking_spaces,
            "amenities": phys.amenities,
            "unit_mix": [
                {"type": u.unit_type, "units": u.count, "avg_sf": u.avg_size_sf,
                 "market_rent": money(fin.market_rents_monthly.get(u.unit_type, 0)),
                 "in_place_rent": money(fin.in_place_rents_monthly.get(u.unit_type, 0)),
                 "market_minus_in_place": money(fin.market_rents_monthly.get(u.unit_type, 0)
                                                - fin.in_place_rents_monthly.get(u.unit_type, 0))}
                for u in phys.unit_mix
            ],
            "physical_occupancy": pct(fin.occupancy.physical_percent),
            "occupied_units": fin.occupancy.occupied_units,
            "vacant_units": fin.occupancy.vacant_units,
            "effective_date": fin.effective_date,
        },
        "market": {
            "submarket": mkt.submarket,
            "submarket_vacancy": pct(mkt.submarket_vacancy_rate),
            "submarket_rent_growth_yoy": pct(mkt.submarket_rent_growth_yoy),
            "rent_comparables": [
                {"name": c.name, "units": c.units, "year_built": c.year_built,
                 "occupancy": pct(c.occupancy), "avg_rent": money(c.avg_rent_per_unit)}
                for c in mkt.comparable_properties
            ],
            "rent_comparables_average_occupancy": pct(
                sum(c.occupancy for c in mkt.comparable_properties) / max(1, len(mkt.comparable_properties))),
            "sale_comparables_average_cap_rate": pct(
                sum(s.cap_rate for s in mkt.comparable_sales) / max(1, len(mkt.comparable_sales))),
            "sale_comparables": [
                {"property": s.property, "date": s.sale_date, "price": money(s.sale_price),
                 "price_per_unit": money(s.price_per_unit), "cap_rate": pct(s.cap_rate)}
                for s in mkt.comparable_sales
            ],
        },
        "loan": {
            "purpose": loan.loan_purpose, "tier": loan.tier, "product": loan.product,
            "loan_amount": money(loan.loan_amount), "loan_per_unit": money(loan.loan_per_unit),
            "note_rate": pct(loan.note_rate), "underwriting_rate": pct(loan.underwriting_rate_basis),
            "term_months": loan.term_months, "amortization_months": loan.amortization_months,
            "interest_only_months": loan.interest_only_months, "prepayment": loan.prepayment_terms,
            "tier_min_dscr": ratio(loan.tier_minimum_dscr), "tier_max_ltv": pct(loan.tier_maximum_ltv),
            "underwritten_dscr": ratio(loan.underwritten_dscr), "actual_dscr": ratio(loan.actual_dscr),
            "ltv_underwriting_value": pct(loan.ltv_underwriting_value),
            "ltv_appraised_value": pct(loan.ltv_appraised_value),
            "debt_yield": pct(loan.debt_yield), "breakeven_occupancy": pct(loan.breakeven_occupancy),
            "binding_constraint": loan.binding_constraint,
            "dscr_constrained_amount": money(loan.dscr_constrained_amount),
            "ltv_constrained_amount": money(loan.ltv_constrained_amount),
            "annual_debt_service_note_rate": money(loan.annual_debt_service_note),
            "annual_debt_service_underwriting_rate": money(loan.annual_debt_service_underwriting),
            "purchase_price": money(loan.purchase_price) if loan.purchase_price else None,
            "dscr_sensitivity": [
                {"rate": pct(rate), "debt_service": money(debt), "dscr": ratio(dscr)}
                for rate, debt, dscr in tables.dscr_sensitivity(cw)
            ],
        },
        "valuation": {
            "appraised_value": money(val.final_value_conclusion.market_value),
            "value_per_unit": money(val.final_value_conclusion.value_per_unit),
            "cap_rate": pct(val.income_approach.cap_rate),
            "income_approach_value": money(val.income_approach.indicated_value),
            "sales_comparison_value": money(val.sales_comparison_approach.indicated_value),
            "underwriting_value": money(loan.underwriting_value),
            "appraiser_noi_after_reserves": money(fin.net_operating_income),
            "appraiser_egi": money(fin.pro_forma_income.effective_gross_income),
        },
        "operations": {
            "year_1_period": f"{y1.period_start} to {y1.period_end}",
            "year_1_egi": money(y1.effective_gross_income), "year_1_opex": money(y1.total_operating_expenses),
            "year_1_noi": money(y1.noi), "year_2_noi": money(hist.year_2.noi), "year_3_noi": money(hist.year_3.noi),
            "underwritten_gpr": money(uw.gpr), "underwritten_egi": money(uw.effective_gross_income),
            "underwritten_opex": money(uw.total_operating_expenses), "underwritten_noi": money(uw.noi),
            "underwritten_ncf": money(uw.ncf),
            "underwritten_expense_ratio": pct(uw.total_operating_expenses / uw.effective_gross_income * 100),
            "underwritten_economic_vacancy": pct((uw.vacancy + uw.concessions + uw.bad_debt) / uw.gpr * 100),
            "underwritten_management_fee": money(uw.management_fee),
            "replacement_reserve_per_unit": money(uw.replacement_reserves / phys.total_units),
            "material_variances_year1_vs_underwritten": tables.material_variances(cw),
            "noi_change_year3_to_year1": money(y1.noi - hist.year_3.noi),
            "underwritten_noi_vs_year1": money(uw.noi - y1.noi),
        },
        "refinance": {
            "maturity_year": refi["year"], "projected_ncf": money(refi["ncf"]),
            "balloon_balance": money(refi["balloon"]), "refinance_rate": pct(refi["refi_rate"]),
            "refinance_dscr": ratio(refi["refi_dscr"]),
        },
    }
    facts["conventions"] = {
        "repair_escrow_factor": "125%", "income_growth": "2%", "tax_growth": "3%",
        "expense_growth": "2%", "refinance_spread": "100 bps", "minimum_economic_vacancy": "5%",
        "minimum_management_fee": "3%", "minimum_reserve_per_unit": money(200),
    }
    if sp:
        facts["sponsorship"] = {
            "borrower": sp.borrower_name, "borrower_type": sp.borrower_type, "guarantor": sp.guarantor,
            "key_principals": [
                {"name": p.name, "role": p.role, "years_experience": p.years_experience,
                 "units_owned": p.units_owned, "net_worth": money(p.net_worth), "liquidity": money(p.liquidity)}
                for p in sp.key_principals
            ],
            "aggregate_net_worth": money(sum(p.net_worth for p in sp.key_principals)),
            "aggregate_liquidity": money(sum(p.liquidity for p in sp.key_principals)),
            "management_company": sp.property_management.name,
            "management_fee": pct(sp.property_management.management_fee_percent),
            "on_site_staffing": sp.property_management.on_site_staffing,
        }
    if tpr:
        pca, esa = tpr.property_condition_assessment, tpr.environmental_site_assessment
        facts["third_party_reports"] = {
            "appraisal": f"{tpr.appraisal.firm}, {tpr.appraisal.date}, {money(tpr.appraisal.value)}",
            "pca": f"{pca.firm}, {pca.date}",
            "pca_immediate_repairs": money(pca.immediate_repairs),
            "pca_repair_escrow_125pct": money(pca.immediate_repairs * 1.25),
            "pca_twelve_year_reserve_need": money(pca.twelve_year_reserve_need),
            "esa": f"{esa.firm}, {esa.date}: {esa.finding}",
            "seismic": "required" if tpr.seismic_applicable else "not required",
            "zoning": tpr.zoning_status,
        }
    return facts
