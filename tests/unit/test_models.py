"""Unit tests for the crosswalk data models."""

import json

import pytest
from pydantic import ValidationError

from lambdas.shared.models import (
    ComparableProperty,
    ComparableSale,
    CrosswalkData,
    FinancialData,
    FinalValueConclusion,
    HistoricalYear,
    IncomeApproach,
    MarketData,
    Occupancy,
    ProFormaExpenses,
    ProFormaIncome,
    PropertyIdentification,
    PropertyPhysical,
    SalesComparisonApproach,
    UnitMixItem,
    UserInput,
    Valuation,
)


# --- Fixtures ---

@pytest.fixture
def sample_unit_mix():
    return [
        UnitMixItem(unit_type="Studio", count=20, avg_size_sf=450, total_sf=9000, bedrooms=0, bathrooms=1),
        UnitMixItem(unit_type="1BR/1BA", count=80, avg_size_sf=700, total_sf=56000, bedrooms=1, bathrooms=1),
        UnitMixItem(unit_type="2BR/2BA", count=75, avg_size_sf=950, total_sf=71250, bedrooms=2, bathrooms=2),
        UnitMixItem(unit_type="3BR/2BA", count=25, avg_size_sf=1200, total_sf=30000, bedrooms=3, bathrooms=2),
    ]


@pytest.fixture
def sample_crosswalk_dict():
    """Full sample crosswalk data as a dict."""
    return {
        "job_id": "test-uuid",
        "generated_at": "2026-02-10T10:30:00Z",
        "property_identification": {
            "property_name": "Maple Ridge Apartments",
            "address": "1234 Main Street",
            "city": "Denver",
            "state": "CO",
            "zip": "80202",
            "county": "Denver County",
            "legal_description": "Lot 5, Block 12",
            "tax_parcel_numbers": ["123-456-789"],
            "current_owner": "Maple Ridge Holdings LLC",
            "year_built": 2018,
            "effective_age": 5,
        },
        "property_physical": {
            "total_units": 200,
            "total_buildings": 8,
            "building_type": "garden-style",
            "stories": 3,
            "gross_building_area_sf": 166250,
            "site_area_acres": 8.5,
            "site_area_sf": 370260,
            "parking_spaces": 350,
            "parking_ratio": 1.75,
            "unit_mix": [
                {"unit_type": "Studio", "count": 20, "avg_size_sf": 450, "total_sf": 9000, "bedrooms": 0, "bathrooms": 1},
                {"unit_type": "1BR/1BA", "count": 80, "avg_size_sf": 700, "total_sf": 56000, "bedrooms": 1, "bathrooms": 1},
                {"unit_type": "2BR/2BA", "count": 75, "avg_size_sf": 950, "total_sf": 71250, "bedrooms": 2, "bathrooms": 2},
                {"unit_type": "3BR/2BA", "count": 25, "avg_size_sf": 1200, "total_sf": 30000, "bedrooms": 3, "bathrooms": 2},
            ],
            "amenities": ["Swimming pool", "Fitness center", "Clubhouse"],
        },
        "market_data": {
            "submarket": "Central Denver",
            "submarket_vacancy_rate": 5.2,
            "submarket_rent_growth_yoy": 4.5,
            "comparable_properties": [
                {"name": "Riverside Gardens", "address": "123 River Rd", "units": 180, "year_built": 2016, "occupancy": 94, "avg_rent_per_unit": 1425},
            ],
            "comparable_sales": [
                {"property": "Riverside Gardens", "sale_date": "2025-06-15", "sale_price": 28500000, "units": 180, "price_per_unit": 158333, "cap_rate": 7.1, "noi": 2023500},
            ],
        },
        "financial_data": {
            "effective_date": "2026-02-10",
            "occupancy": {"physical_percent": 92.5, "occupied_units": 185, "vacant_units": 15},
            "market_rents_monthly": {"Studio": 950, "1BR/1BA": 1350, "2BR/2BA": 1650, "3BR/2BA": 1950},
            "in_place_rents_monthly": {"Studio": 925, "1BR/1BA": 1325, "2BR/2BA": 1600, "3BR/2BA": 1875},
            "pro_forma_income": {
                "potential_gross_rental_income": 3240000,
                "other_income": 100000,
                "potential_gross_income": 3340000,
                "vacancy_collection_loss_percent": 7.0,
                "vacancy_collection_loss_amount": 233800,
                "effective_gross_income": 3106200,
            },
            "pro_forma_expenses": {
                "real_estate_taxes": 180000,
                "insurance": 50000,
                "utilities": 75000,
                "repairs_maintenance": 70000,
                "payroll": 100000,
                "management_fee_percent": 4.0,
                "management_fee_amount": 124248,
                "marketing": 20000,
                "administrative": 25000,
                "replacement_reserves": 60000,
                "total_operating_expenses": 704248,
                "expense_per_unit": 3521,
            },
            "net_operating_income": 2401952,
            "historical_t12": {
                "year_1": {
                    "rental_income": 2750000, "other_income": 85000, "vacancy_loss": -275000,
                    "effective_gross_income": 2560000, "operating_expenses": 599400, "net_operating_income": 1960600,
                },
                "year_2": {
                    "rental_income": 2900000, "other_income": 90000, "vacancy_loss": -255000,
                    "effective_gross_income": 2735000, "operating_expenses": 625000, "net_operating_income": 2110000,
                },
                "year_3": {
                    "rental_income": 3050000, "other_income": 95000, "vacancy_loss": -245000,
                    "effective_gross_income": 2900000, "operating_expenses": 655000, "net_operating_income": 2245000,
                },
            },
        },
        "valuation": {
            "sales_comparison_approach": {"indicated_value": 32500000, "value_per_unit": 162500, "value_per_sf": 195.49},
            "income_approach": {"stabilized_noi": 2401952, "cap_rate": 7.39, "indicated_value": 32500000},
            "final_value_conclusion": {"market_value": 32500000, "value_per_unit": 162500, "value_per_sf": 195.49, "effective_date": "2026-02-10"},
        },
    }


# --- Unit Mix Tests ---

class TestUnitMixItem:
    def test_valid_unit(self):
        item = UnitMixItem(unit_type="1BR", count=10, avg_size_sf=700, total_sf=7000, bedrooms=1, bathrooms=1)
        assert item.count == 10

    def test_invalid_total_sf(self):
        with pytest.raises(ValidationError, match="total_sf"):
            UnitMixItem(unit_type="1BR", count=10, avg_size_sf=700, total_sf=9999, bedrooms=1, bathrooms=1)


# --- Property Physical Tests ---

class TestPropertyPhysical:
    def test_unit_mix_total_mismatch(self, sample_unit_mix):
        with pytest.raises(ValidationError, match="Unit mix total"):
            PropertyPhysical(
                total_units=999,  # doesn't match unit_mix sum of 200
                total_buildings=8, building_type="garden-style", stories=3,
                gross_building_area_sf=166250, site_area_acres=8.5, site_area_sf=370260,
                parking_spaces=350, parking_ratio=1.75,
                unit_mix=sample_unit_mix, amenities=[],
            )


# --- Financial Validation Tests ---

class TestProFormaIncome:
    def test_pgi_mismatch(self):
        with pytest.raises(ValidationError, match="PGI"):
            ProFormaIncome(
                potential_gross_rental_income=3000000,
                other_income=100000,
                potential_gross_income=9999999,  # wrong
                vacancy_collection_loss_percent=7.0,
                vacancy_collection_loss_amount=233800,
                effective_gross_income=3106200,
            )

    def test_egi_mismatch(self):
        with pytest.raises(ValidationError, match="EGI"):
            ProFormaIncome(
                potential_gross_rental_income=3240000,
                other_income=100000,
                potential_gross_income=3340000,
                vacancy_collection_loss_percent=7.0,
                vacancy_collection_loss_amount=233800,
                effective_gross_income=9999999,  # wrong
            )


class TestHistoricalYear:
    def test_valid_year(self):
        y = HistoricalYear(
            rental_income=2750000, other_income=85000, vacancy_loss=-275000,
            effective_gross_income=2560000, operating_expenses=599400, net_operating_income=1960600,
        )
        assert y.net_operating_income == 1960600

    def test_noi_mismatch(self):
        with pytest.raises(ValidationError, match="NOI"):
            HistoricalYear(
                rental_income=2750000, other_income=85000, vacancy_loss=-275000,
                effective_gross_income=2560000, operating_expenses=599400, net_operating_income=999999,
            )


# --- CrosswalkData Tests ---

class TestCrosswalkData:
    def test_full_model_validation(self, sample_crosswalk_dict):
        data = CrosswalkData.model_validate(sample_crosswalk_dict)
        assert data.property_physical.total_units == 200
        assert data.financial_data.net_operating_income == 2401952
        assert data.valuation.final_value_conclusion.market_value == 32500000

    def test_json_round_trip(self, sample_crosswalk_dict):
        data = CrosswalkData.model_validate(sample_crosswalk_dict)
        json_str = data.to_json()
        data2 = CrosswalkData.from_json(json_str)
        assert data2.property_identification.property_name == "Maple Ridge Apartments"
        assert data2.financial_data.net_operating_income == data.financial_data.net_operating_income

    def test_validate_cap_rate(self, sample_crosswalk_dict):
        data = CrosswalkData.model_validate(sample_crosswalk_dict)
        assert data.validate_cap_rate()

    def test_validate_value_per_unit(self, sample_crosswalk_dict):
        data = CrosswalkData.model_validate(sample_crosswalk_dict)
        assert data.validate_value_per_unit()

    def test_validate_occupancy_units(self, sample_crosswalk_dict):
        data = CrosswalkData.model_validate(sample_crosswalk_dict)
        assert data.validate_occupancy_units()


# --- UserInput Tests ---

class TestUserInput:
    def test_valid_input(self):
        inp = UserInput(
            address="123 Main St", city="Denver", state="CO",
            units=200, year_built=2018, property_type="garden-style",
        )
        assert inp.units == 200

    def test_units_too_low(self):
        with pytest.raises(ValidationError):
            UserInput(address="123 Main St", city="Denver", state="CO", units=5, year_built=2018, property_type="garden-style")

    def test_units_too_high(self):
        with pytest.raises(ValidationError):
            UserInput(address="123 Main St", city="Denver", state="CO", units=999, year_built=2018, property_type="garden-style")

    def test_invalid_property_type(self):
        with pytest.raises(ValidationError):
            UserInput(address="123 Main St", city="Denver", state="CO", units=100, year_built=2018, property_type="townhome")
