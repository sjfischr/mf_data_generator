import boto3
import pytest

try:
    import fal_client
except ImportError:
    fal_client = None

from strands.models import bedrock as strands_bedrock


@pytest.fixture(autouse=True)
def prevent_live_external_clients(monkeypatch):
    original_boto3_client = boto3.client

    def guarded_boto3_client(service_name, *args, **kwargs):
        if service_name in {"bedrock", "bedrock-runtime"}:
            raise RuntimeError(
                "Live Bedrock calls are forbidden in unit tests; mock the Bedrock client "
                "or Strands Agent instead."
            )
        return original_boto3_client(service_name, *args, **kwargs)

    monkeypatch.setattr(boto3, "client", guarded_boto3_client)

    def guarded_bedrock_model_init(self, *args, **kwargs):
        raise RuntimeError(
            "Live Strands BedrockModel construction is forbidden in unit tests."
        )

    monkeypatch.setattr(
        strands_bedrock.BedrockModel,
        "__init__",
        guarded_bedrock_model_init,
    )

    if fal_client is not None:
        def guarded_fal_run(*args, **kwargs):
            raise RuntimeError(
                "Outbound fal.ai calls are forbidden in unit tests; mock fal_client.run."
            )

        monkeypatch.setattr(fal_client, "run", guarded_fal_run)


USER_INPUT = {
    "property_name": "Maple Ridge Apartments",
    "address": "1234 Main Street",
    "city": "Denver",
    "state": "CO",
    "units": 200,
    "year_built": 2008,
    "property_type": "garden-style",
}


def messy_llm_draft() -> dict:
    """A realistic Haiku draft: wrong arithmetic, alias keys, signed deductions, missing ESA."""
    return {
        "property_identification": {
            "property_name": "Maple Ridge Apartments", "address": "1234 Main Street", "city": "Denver",
            "state": "CO", "zip": "80202", "county": "Denver County", "legal_description": "Lot 1, Block 1",
            "tax_parcel_numbers": ["111-222-333"], "current_owner": "Maple Ridge LLC",
            "year_built": 2008, "effective_age": 12,
        },
        "property_physical": {
            "total_units": 200, "total_buildings": 8, "building_type": "garden-style", "stories": 3,
            "gross_building_area_sf": 150000, "site_area_acres": 8.0, "site_area_sf": 1,
            "parking_spaces": 300, "parking_ratio": 9.9,
            "unit_mix": [
                {"unit_type": "1BR/1BA", "count": 100, "avg_size_sf": 700, "total_sf": 1, "bedrooms": 1, "bathrooms": 1},
                {"unit_type": "2BR/2BA", "count": 90, "avg_size_sf": 950, "total_sf": 1, "bedrooms": 2, "bathrooms": 2},
            ],
            "amenities": ["Pool", "Fitness center"],
        },
        "market_data": {
            "submarket": "Central Denver", "submarket_vacancy_rate": 5.5, "submarket_rent_growth_yoy": 3.0,
            "comparable_properties": [
                {"name": "Comp A", "address": "1 St", "units": 180, "year_built": 2010, "occupancy": 95, "avg_rent_per_unit": 1650},
            ],
            "comparable_sales": [
                {"property": "Comp A", "sale_date": "2026-03-01", "sale_price": 40000000, "units": 180,
                 "price_per_unit": 999, "cap_rate": 5.4, "noi": 1},
            ],
        },
        "financial_data": {
            "effective_date": "2024-01-01",
            "occupancy": {"physical_percent": 94.5, "occupied_units": 1, "vacant_units": 1},
            "market_rents_monthly": {"1BR/1BA": 1500, "2BR/2BA": 1900},
            "in_place_rents_monthly": {"1BR/1BA": 1460, "2BR/2BA": 1850},
            "pro_forma_income": {"potential_gross_rental_income": 1, "other_income": 120000,
                                 "potential_gross_income": 1, "vacancy_collection_loss_percent": 6.0,
                                 "vacancy_collection_loss_amount": 1, "effective_gross_income": 1},
            "pro_forma_expenses": {"real_estate_taxes": 520000, "insurance": 140000, "utilities": 210000,
                                   "repairs_maintenance": 190000, "payroll": 380000, "management_fee_percent": 3.5,
                                   "management_fee_amount": 1, "marketing": 40000, "administrative": 90000,
                                   "replacement_reserves": 50000, "total_operating_expenses": 1, "expense_per_unit": 1},
            "net_operating_income": 1,
            "historical_t12": {"Year 1": {"rental_income": 1, "other_income": 1, "vacancy_loss": -1,
                                          "effective_gross_income": 99, "operating_expenses": 1, "net_operating_income": 1}},
        },
        "valuation": {
            "sales_comparison_approach": {"indicated_value": 52000000, "value_per_unit": 1, "value_per_sf": 1},
            "income_approach": {"stabilized_noi": 1, "cap_rate": 5.5, "indicated_value": 1},
            "final_value_conclusion": {"market_value": 1, "value_per_unit": 1, "value_per_sf": 1, "effective_date": "2024-01-01"},
        },
        "operating_year1": {
            "potential_gross_rental_income": 4100000, "loss_to_lease": -40000, "vacancy": -205000,
            "concessions": -30000, "bad_debt": -20000, "laundry": 45000, "parking_income": 40000,
            "other_income": 30000, "real_estate_taxes": 500000, "insurance": 135000, "utilities": 140000,
            "water_sewer": 70000, "repairs_maintenance": 185000, "payroll": 370000, "administrative": 70000,
            "marketing": 38000, "professional_fees": 18000, "management_fee_amount": 135000,
            "replacement_reserves": 50000,
        },
        "financing_inputs": {"loan_purpose": "Acquisition and Stabilization", "tier": "Tier 1",
                             "note_rate": 5.75, "term_months": 360, "purchase_price": 1},
        "sponsorship": {
            "borrower_name": "Maple Ridge Owner LLC", "borrower_type": "LLC",
            "key_principals": [{"name": "Pat Example", "title": "Managing Partner", "experience_years": 18}],
            "guarantor": "Pat Example",
            "property_management": {"company_name": "Example Management", "fee_percent": 3.5},
        },
        "third_party_reports": {
            "appraisal": {"appraiser_name": "Example Appraisal", "appraisal_value": 1},
            "property_condition": {"inspector": "Example PCA", "deferred_maintenance": 60000},
            "seismic": {"retrofit_required": False},
            "zoning": {"zoning_classification": "R-3"},
        },
    }


@pytest.fixture
def llm_draft():
    return messy_llm_draft()


@pytest.fixture
def finalized_crosswalk():
    from datetime import date

    from lambdas.shared.crosswalk_repair import repair_draft
    from lambdas.shared.models import CrosswalkDraft
    from lambdas.shared.underwriting import finalize_crosswalk

    repaired = repair_draft(messy_llm_draft(), USER_INPUT, "test-job", today=date(2026, 11, 15))
    return finalize_crosswalk(CrosswalkDraft.model_validate(repaired))
