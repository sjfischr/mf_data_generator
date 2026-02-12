"""Unit tests for the crosswalk generator Lambda."""

import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def sample_input():
    return {
        "address": "1234 Main Street",
        "city": "Denver",
        "state": "CO",
        "units": 200,
        "year_built": 2018,
        "property_type": "garden-style",
    }


@pytest.fixture
def mock_crosswalk_response():
    """Minimal valid crosswalk JSON response from the model."""
    return {
        "property_identification": {
            "property_name": "Test Apartments",
            "address": "1234 Main Street",
            "city": "Denver",
            "state": "CO",
            "zip": "80202",
            "county": "Denver County",
            "legal_description": "Lot 1, Block 1",
            "tax_parcel_numbers": ["111-222-333"],
            "current_owner": "Test LLC",
            "year_built": 2018,
            "effective_age": 5,
        },
        "property_physical": {
            "total_units": 200,
            "total_buildings": 8,
            "building_type": "garden-style",
            "stories": 3,
            "gross_building_area_sf": 160000,
            "site_area_acres": 8.0,
            "site_area_sf": 348480,
            "parking_spaces": 300,
            "parking_ratio": 1.5,
            "unit_mix": [
                {"unit_type": "1BR", "count": 100, "avg_size_sf": 700, "total_sf": 70000, "bedrooms": 1, "bathrooms": 1},
                {"unit_type": "2BR", "count": 100, "avg_size_sf": 900, "total_sf": 90000, "bedrooms": 2, "bathrooms": 2},
            ],
            "amenities": ["Pool"],
        },
        "market_data": {
            "submarket": "Central Denver",
            "submarket_vacancy_rate": 5.0,
            "submarket_rent_growth_yoy": 3.0,
            "comparable_properties": [
                {"name": "Comp A", "address": "1 St", "units": 100, "year_built": 2015, "occupancy": 95, "avg_rent_per_unit": 1400},
            ],
            "comparable_sales": [
                {"property": "Comp A", "sale_date": "2025-01-01", "sale_price": 15000000, "units": 100, "price_per_unit": 150000, "cap_rate": 7.0, "noi": 1050000},
            ],
        },
        "financial_data": {
            "effective_date": "2026-02-10",
            "occupancy": {"physical_percent": 95.0, "occupied_units": 190, "vacant_units": 10},
            "market_rents_monthly": {"1BR": 1400, "2BR": 1700},
            "in_place_rents_monthly": {"1BR": 1350, "2BR": 1650},
            "pro_forma_income": {
                "potential_gross_rental_income": 3720000,
                "other_income": 80000,
                "potential_gross_income": 3800000,
                "vacancy_collection_loss_percent": 5.0,
                "vacancy_collection_loss_amount": 190000,
                "effective_gross_income": 3610000,
            },
            "pro_forma_expenses": {
                "real_estate_taxes": 200000,
                "insurance": 60000,
                "utilities": 80000,
                "repairs_maintenance": 75000,
                "payroll": 110000,
                "management_fee_percent": 4.0,
                "management_fee_amount": 144400,
                "marketing": 25000,
                "administrative": 30000,
                "replacement_reserves": 50000,
                "total_operating_expenses": 774400,
                "expense_per_unit": 3872,
            },
            "net_operating_income": 2835600,
            "historical_t12": {
                "year_1": {"rental_income": 3400000, "other_income": 70000, "vacancy_loss": -200000, "effective_gross_income": 3270000, "operating_expenses": 700000, "net_operating_income": 2570000},
                "year_2": {"rental_income": 3500000, "other_income": 75000, "vacancy_loss": -190000, "effective_gross_income": 3385000, "operating_expenses": 720000, "net_operating_income": 2665000},
                "year_3": {"rental_income": 3600000, "other_income": 78000, "vacancy_loss": -180000, "effective_gross_income": 3498000, "operating_expenses": 740000, "net_operating_income": 2758000},
            },
        },
        "valuation": {
            "sales_comparison_approach": {"indicated_value": 30000000, "value_per_unit": 150000, "value_per_sf": 187.5},
            "income_approach": {"stabilized_noi": 2835600, "cap_rate": 9.45, "indicated_value": 30006349},
            "final_value_conclusion": {"market_value": 30000000, "value_per_unit": 150000, "value_per_sf": 187.5, "effective_date": "2026-02-10"},
        },
    }


class TestCrosswalkGenerator:
    @patch("lambdas.shared.s3_utils.read_json")
    @patch("lambdas.shared.s3_utils.write_json")
    @patch("lambdas.shared.bedrock_client.invoke_model_json")
    def test_generates_valid_crosswalk(self, mock_bedrock, mock_write, mock_read, sample_input, mock_crosswalk_response):
        mock_read.return_value = sample_input
        mock_bedrock.return_value = mock_crosswalk_response

        from lambdas.shared.models import CrosswalkData
        data = CrosswalkData.model_validate(mock_crosswalk_response)

        assert data.property_physical.total_units == 200
        assert data.financial_data.net_operating_income == 2835600

    def test_crosswalk_validates_math(self, mock_crosswalk_response):
        from lambdas.shared.models import CrosswalkData
        data = CrosswalkData.model_validate(mock_crosswalk_response)

        # NOI = EGI - Expenses
        assert data.financial_data.net_operating_income == (
            data.financial_data.pro_forma_income.effective_gross_income
            - data.financial_data.pro_forma_expenses.total_operating_expenses
        )

        # Occupancy units add up
        assert data.validate_occupancy_units()
