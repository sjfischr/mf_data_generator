"""Pydantic V2 models for the Crosswalk Data Schema.

This is the contract between all agents. The CrosswalkData model is the master
schema that every Lambda reads from and validates against.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class PropertyIdentification(BaseModel):
    """Core property identification data."""

    property_name: str
    address: str
    city: str
    state: str = Field(min_length=2, max_length=2)
    zip: str = Field(pattern=r"^\d{5}(-\d{4})?$")
    county: str
    legal_description: str
    tax_parcel_numbers: list[str]
    current_owner: str
    year_built: int = Field(ge=1900, le=2030)
    effective_age: int = Field(ge=0, le=130)


class UnitMixItem(BaseModel):
    """A single row in the unit mix table."""

    unit_type: str
    count: int = Field(gt=0)
    avg_size_sf: int = Field(gt=0)
    total_sf: int = Field(gt=0)
    bedrooms: int = Field(ge=0)
    bathrooms: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_total_sf(self) -> "UnitMixItem":
        expected = self.count * self.avg_size_sf
        if self.total_sf != expected:
            raise ValueError(
                f"total_sf ({self.total_sf}) != count * avg_size_sf ({expected})"
            )
        return self


class PropertyPhysical(BaseModel):
    """Physical characteristics of the property."""

    total_units: int = Field(ge=1, le=2000)
    total_buildings: int = Field(ge=1)
    building_type: Literal["garden-style", "mid-rise", "high-rise"]
    stories: int = Field(ge=1, le=100)
    gross_building_area_sf: int = Field(gt=0)
    site_area_acres: float = Field(gt=0)
    site_area_sf: int = Field(gt=0)
    parking_spaces: int = Field(ge=0)
    parking_ratio: float = Field(ge=0)
    unit_mix: list[UnitMixItem]
    amenities: list[str]

    @model_validator(mode="after")
    def validate_unit_mix_totals(self) -> "PropertyPhysical":
        total_from_mix = sum(item.count for item in self.unit_mix)
        if total_from_mix != self.total_units:
            raise ValueError(
                f"Unit mix total ({total_from_mix}) != total_units ({self.total_units})"
            )
        return self


class ComparableProperty(BaseModel):
    """A comparable rental property."""

    name: str
    address: str
    units: int = Field(gt=0)
    year_built: int = Field(ge=1900, le=2030)
    occupancy: float = Field(ge=0, le=100)
    avg_rent_per_unit: float = Field(gt=0)


class ComparableSale(BaseModel):
    """A comparable property sale transaction."""

    property: str
    sale_date: str
    sale_price: int = Field(gt=0)
    units: int = Field(gt=0)
    price_per_unit: int = Field(gt=0)
    cap_rate: float = Field(gt=0, le=100)
    noi: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_price_per_unit(self) -> "ComparableSale":
        expected = round(self.sale_price / self.units)
        if abs(self.price_per_unit - expected) > 1:
            raise ValueError(
                f"price_per_unit ({self.price_per_unit}) != "
                f"sale_price / units ({expected})"
            )
        return self


class MarketData(BaseModel):
    """Market and comparable data."""

    submarket: str
    submarket_vacancy_rate: float = Field(ge=0, le=100)
    submarket_rent_growth_yoy: float
    comparable_properties: list[ComparableProperty] = Field(min_length=1)
    comparable_sales: list[ComparableSale] = Field(min_length=1)


class Occupancy(BaseModel):
    """Current occupancy metrics."""

    physical_percent: float = Field(ge=0, le=100)
    occupied_units: int = Field(ge=0)
    vacant_units: int = Field(ge=0)


class ProFormaIncome(BaseModel):
    """Projected income statement."""

    potential_gross_rental_income: int = Field(gt=0)
    other_income: int = Field(ge=0)
    potential_gross_income: int = Field(gt=0)
    vacancy_collection_loss_percent: float = Field(ge=0, le=100)
    vacancy_collection_loss_amount: int = Field(ge=0)
    effective_gross_income: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_income_math(self) -> "ProFormaIncome":
        expected_pgi = self.potential_gross_rental_income + self.other_income
        if self.potential_gross_income != expected_pgi:
            raise ValueError(
                f"PGI ({self.potential_gross_income}) != "
                f"rental + other ({expected_pgi})"
            )
        expected_egi = self.potential_gross_income - self.vacancy_collection_loss_amount
        if self.effective_gross_income != expected_egi:
            raise ValueError(
                f"EGI ({self.effective_gross_income}) != "
                f"PGI - vacancy ({expected_egi})"
            )
        return self


class ProFormaExpenses(BaseModel):
    """Projected operating expenses."""

    real_estate_taxes: int = Field(ge=0)
    insurance: int = Field(ge=0)
    utilities: int = Field(ge=0)
    repairs_maintenance: int = Field(ge=0)
    payroll: int = Field(ge=0)
    management_fee_percent: float = Field(ge=0, le=100)
    management_fee_amount: int = Field(ge=0)
    marketing: int = Field(ge=0)
    administrative: int = Field(ge=0)
    replacement_reserves: int = Field(ge=0)
    total_operating_expenses: int = Field(ge=0)
    expense_per_unit: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_expense_totals(self) -> "ProFormaExpenses":
        calculated = (
            self.real_estate_taxes
            + self.insurance
            + self.utilities
            + self.repairs_maintenance
            + self.payroll
            + self.management_fee_amount
            + self.marketing
            + self.administrative
            + self.replacement_reserves
        )
        if self.total_operating_expenses != calculated:
            raise ValueError(
                f"total_operating_expenses ({self.total_operating_expenses}) != "
                f"sum of line items ({calculated})"
            )
        return self


class HistoricalYear(BaseModel):
    """One year of historical operating data."""

    rental_income: int
    other_income: int
    vacancy_loss: int  # negative value
    effective_gross_income: int
    operating_expenses: int
    net_operating_income: int

    @model_validator(mode="after")
    def validate_noi(self) -> "HistoricalYear":
        expected_egi = self.rental_income + self.other_income + self.vacancy_loss
        if self.effective_gross_income != expected_egi:
            raise ValueError(
                f"EGI ({self.effective_gross_income}) != "
                f"rental + other + vacancy ({expected_egi})"
            )
        expected_noi = self.effective_gross_income - self.operating_expenses
        if self.net_operating_income != expected_noi:
            raise ValueError(
                f"NOI ({self.net_operating_income}) != "
                f"EGI - expenses ({expected_noi})"
            )
        return self


class FinancialData(BaseModel):
    """Complete financial data package."""

    effective_date: str
    occupancy: Occupancy
    market_rents_monthly: dict[str, int]
    in_place_rents_monthly: dict[str, int]
    pro_forma_income: ProFormaIncome
    pro_forma_expenses: ProFormaExpenses
    net_operating_income: int = Field(gt=0)
    historical_t12: dict[str, HistoricalYear]

    @model_validator(mode="after")
    def validate_noi_calculation(self) -> "FinancialData":
        expected = (
            self.pro_forma_income.effective_gross_income
            - self.pro_forma_expenses.total_operating_expenses
        )
        if self.net_operating_income != expected:
            raise ValueError(
                f"NOI ({self.net_operating_income}) != EGI - expenses ({expected})"
            )
        return self


class SalesComparisonApproach(BaseModel):
    """Sales comparison approach value indication."""

    indicated_value: int = Field(gt=0)
    value_per_unit: int = Field(gt=0)
    value_per_sf: float = Field(gt=0)


class IncomeApproach(BaseModel):
    """Income capitalization approach value indication."""

    stabilized_noi: int = Field(gt=0)
    cap_rate: float = Field(gt=0, le=100)
    indicated_value: int = Field(gt=0)


class FinalValueConclusion(BaseModel):
    """Reconciled final value conclusion."""

    market_value: int = Field(gt=0)
    value_per_unit: int = Field(gt=0)
    value_per_sf: float = Field(gt=0)
    effective_date: str


class Valuation(BaseModel):
    """All valuation approaches and final conclusion."""

    sales_comparison_approach: SalesComparisonApproach
    income_approach: IncomeApproach
    final_value_conclusion: FinalValueConclusion


class CrosswalkData(BaseModel):
    """Master crosswalk data schema — the contract between all agents."""

    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    generated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    property_identification: PropertyIdentification
    property_physical: PropertyPhysical
    market_data: MarketData
    financial_data: FinancialData
    valuation: Valuation

    def validate_cap_rate(self) -> bool:
        """Verify cap rate = NOI / Value."""
        noi = self.valuation.income_approach.stabilized_noi
        value = self.valuation.income_approach.indicated_value
        expected_rate = round((noi / value) * 100, 2)
        actual_rate = self.valuation.income_approach.cap_rate
        return abs(actual_rate - expected_rate) < 0.05

    def validate_value_per_unit(self) -> bool:
        """Verify value/unit = market_value / total_units."""
        value = self.valuation.final_value_conclusion.market_value
        units = self.property_physical.total_units
        expected = round(value / units)
        actual = self.valuation.final_value_conclusion.value_per_unit
        return abs(actual - expected) <= 1

    def validate_occupancy_units(self) -> bool:
        """Verify occupied + vacant = total units."""
        occ = self.financial_data.occupancy
        total = self.property_physical.total_units
        return occ.occupied_units + occ.vacant_units == total

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, data: str) -> "CrosswalkData":
        return cls.model_validate_json(data)


class UserInput(BaseModel):
    """Input from the frontend form."""

    address: str = Field(min_length=1)
    city: str = Field(min_length=1)
    state: str = Field(min_length=2, max_length=2)
    units: int = Field(ge=10, le=500)
    year_built: int = Field(ge=1950, le=2026)
    property_type: Literal["garden-style", "mid-rise", "high-rise"]
