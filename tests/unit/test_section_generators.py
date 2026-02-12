"""Unit tests for the section generator base class and section handlers."""

from unittest.mock import MagicMock, patch

import pytest

from lambdas.shared.models import CrosswalkData


@pytest.fixture
def sample_crosswalk_dict():
    """Minimal valid crosswalk for section generator tests."""
    return {
        "job_id": "test-job-123",
        "generated_at": "2026-02-10T10:30:00Z",
        "property_identification": {
            "property_name": "Test Apartments",
            "address": "100 Test Ave",
            "city": "Denver",
            "state": "CO",
            "zip": "80202",
            "county": "Denver County",
            "legal_description": "Lot 1",
            "tax_parcel_numbers": ["111-222"],
            "current_owner": "Test LLC",
            "year_built": 2020,
            "effective_age": 3,
        },
        "property_physical": {
            "total_units": 50,
            "total_buildings": 2,
            "building_type": "garden-style",
            "stories": 3,
            "gross_building_area_sf": 37500,
            "site_area_acres": 2.0,
            "site_area_sf": 87120,
            "parking_spaces": 75,
            "parking_ratio": 1.5,
            "unit_mix": [
                {"unit_type": "1BR", "count": 30, "avg_size_sf": 700, "total_sf": 21000, "bedrooms": 1, "bathrooms": 1},
                {"unit_type": "2BR", "count": 20, "avg_size_sf": 900, "total_sf": 18000, "bedrooms": 2, "bathrooms": 2},
            ],
            "amenities": ["Pool"],
        },
        "market_data": {
            "submarket": "Central Denver",
            "submarket_vacancy_rate": 5.0,
            "submarket_rent_growth_yoy": 3.0,
            "comparable_properties": [
                {"name": "Comp", "address": "1 St", "units": 40, "year_built": 2018, "occupancy": 94, "avg_rent_per_unit": 1300},
            ],
            "comparable_sales": [
                {"property": "Comp", "sale_date": "2025-06-01", "sale_price": 6000000, "units": 40, "price_per_unit": 150000, "cap_rate": 7.0, "noi": 420000},
            ],
        },
        "financial_data": {
            "effective_date": "2026-02-10",
            "occupancy": {"physical_percent": 94.0, "occupied_units": 47, "vacant_units": 3},
            "market_rents_monthly": {"1BR": 1400, "2BR": 1700},
            "in_place_rents_monthly": {"1BR": 1350, "2BR": 1650},
            "pro_forma_income": {
                "potential_gross_rental_income": 900000,
                "other_income": 20000,
                "potential_gross_income": 920000,
                "vacancy_collection_loss_percent": 6.0,
                "vacancy_collection_loss_amount": 55200,
                "effective_gross_income": 864800,
            },
            "pro_forma_expenses": {
                "real_estate_taxes": 50000,
                "insurance": 15000,
                "utilities": 20000,
                "repairs_maintenance": 18000,
                "payroll": 30000,
                "management_fee_percent": 4.0,
                "management_fee_amount": 34592,
                "marketing": 5000,
                "administrative": 8000,
                "replacement_reserves": 15000,
                "total_operating_expenses": 195592,
                "expense_per_unit": 3912,
            },
            "net_operating_income": 669208,
            "historical_t12": {
                "year_1": {"rental_income": 800000, "other_income": 15000, "vacancy_loss": -50000, "effective_gross_income": 765000, "operating_expenses": 175000, "net_operating_income": 590000},
                "year_2": {"rental_income": 840000, "other_income": 17000, "vacancy_loss": -48000, "effective_gross_income": 809000, "operating_expenses": 180000, "net_operating_income": 629000},
                "year_3": {"rental_income": 870000, "other_income": 19000, "vacancy_loss": -45000, "effective_gross_income": 844000, "operating_expenses": 185000, "net_operating_income": 659000},
            },
        },
        "valuation": {
            "sales_comparison_approach": {"indicated_value": 7500000, "value_per_unit": 150000, "value_per_sf": 192.31},
            "income_approach": {"stabilized_noi": 669208, "cap_rate": 8.92, "indicated_value": 7502332},
            "final_value_conclusion": {"market_value": 7500000, "value_per_unit": 150000, "value_per_sf": 192.31, "effective_date": "2026-02-10"},
        },
    }


class TestSectionGeneratorBase:
    @patch("lambdas.shared.s3_utils.read_json")
    def test_load_crosswalk_data(self, mock_read, sample_crosswalk_dict):
        mock_read.return_value = sample_crosswalk_dict
        from lambdas.shared.section_generator import SectionGenerator

        class TestSection(SectionGenerator):
            def get_section_name(self): return "test_section"
            def get_model_name(self): return "haiku"
            def get_system_prompt(self): return "Test prompt"
            def build_prompt(self, crosswalk): return "Generate test"

        event = {"job_id": "test-job-123"}
        gen = TestSection(event, None)
        crosswalk = gen.load_crosswalk_data()

        assert crosswalk.property_identification.property_name == "Test Apartments"
        assert crosswalk.property_physical.total_units == 50

    @patch("lambdas.shared.s3_utils.write_text")
    @patch("lambdas.shared.bedrock_client.invoke_model")
    @patch("lambdas.shared.s3_utils.read_json")
    def test_execute_full_pipeline(self, mock_read, mock_bedrock, mock_write, sample_crosswalk_dict):
        mock_read.return_value = sample_crosswalk_dict
        mock_bedrock.return_value = "# Section 1\n\nGenerated content here."
        mock_write.return_value = "jobs/test-job-123/sections/test_section.md"

        from lambdas.shared.section_generator import SectionGenerator

        class TestSection(SectionGenerator):
            def get_section_name(self): return "test_section"
            def get_model_name(self): return "haiku"
            def get_system_prompt(self): return "You are an appraiser."
            def build_prompt(self, crosswalk): return f"Write about {crosswalk.property_identification.property_name}"

        event = {"job_id": "test-job-123"}
        result = TestSection(event, None).execute()

        assert result["status"] == "success"
        assert result["section"] == "test_section"
        mock_bedrock.assert_called_once()
        mock_write.assert_called_once()
