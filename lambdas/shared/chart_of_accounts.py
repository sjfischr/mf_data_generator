"""Fannie Mae-aligned chart of accounts and deterministic allocation helpers."""

from __future__ import annotations

import hashlib
import random


WARM_CLIMATE_STATES = {
    "FL", "AZ", "TX", "CA", "HI", "LA", "GA", "SC", "AL", "MS",
}


CHART_OF_ACCOUNTS = [
    # Revenue
    ("4010", "Gross Potential Rent", "gpr", "level", 50),
    ("4020", "Loss/Gain to Lease", "loss_gain_to_lease", "level", 50),
    ("4030", "Physical Vacancy", "vacancy", "seasonal", 60),
    ("4040", "Concessions", "concessions", "seasonal", 70),
    ("4050", "Bad Debt", "bad_debt", "seasonal", 50),
    ("4060", "Non-Revenue Units", "non_revenue_units", "level", 40),
    ("4110", "Laundry and Vending", "laundry_vending", "level", 50),
    ("4120", "Parking Income", "parking", "level", 50),
    ("4130", "Commercial Income", "commercial", "level", 50),
    ("4140", "Application Fees", "other_income", "summer_peak", 20),
    ("4150", "Late Fees and NSF Fees", "other_income", "seasonal", 15),
    ("4160", "Pet Fees", "other_income", "level", 15),
    ("4170", "Storage Income", "other_income", "level", 10),
    ("4180", "RUBS / Utility Income", "other_income", "heating_cooling", 20),
    ("4190", "Cable / Internet Income", "other_income", "level", 10),
    ("4200", "Miscellaneous Other Income", "other_income", "seasonal", 10),

    # Expenses
    ("5010", "Property Management Fee", "management_fee", "level", 60),
    ("5020", "Asset Management Fee", "management_fee", "level", 40),
    ("5110", "Manager Salary", "payroll_benefits", "level", 18),
    ("5120", "Leasing Salary", "payroll_benefits", "summer_peak", 14),
    ("5130", "Maintenance Salary", "payroll_benefits", "level", 18),
    ("5140", "Payroll Taxes", "payroll_benefits", "level", 14),
    ("5150", "Benefits", "payroll_benefits", "level", 16),
    ("5160", "Workers Compensation", "payroll_benefits", "level", 10),
    ("5170", "Temporary and Contract Labor", "payroll_benefits", "summer_peak", 10),
    ("5210", "Office and Administrative", "general_administrative", "level", 20),
    ("5220", "Telephone and Internet", "general_administrative", "level", 15),
    ("5230", "Computer and Software", "general_administrative", "level", 15),
    ("5240", "Screening and Leasing Costs", "general_administrative", "summer_peak", 15),
    ("5250", "Licenses and Permits", "general_administrative", "level", 10),
    ("5260", "Bank and Credit Card Fees", "general_administrative", "level", 15),
    ("5270", "Postage, Printing, and Supplies", "general_administrative", "level", 10),
    ("5310", "Advertising", "marketing", "summer_peak", 35),
    ("5320", "Resident Relations", "marketing", "seasonal", 25),
    ("5330", "Promotions and Brokerage", "marketing", "summer_peak", 40),
    ("5410", "Accounting and Audit", "professional_fees", "level", 35),
    ("5420", "Legal Services", "professional_fees", "seasonal", 35),
    ("5430", "Tax Preparation", "professional_fees", "level", 30),
    ("5510", "Turnover and Make-Ready", "repairs_maintenance", "summer_peak", 20),
    ("5520", "Appliance Repair", "repairs_maintenance", "seasonal", 10),
    ("5530", "HVAC Repair", "repairs_maintenance", "heating_cooling", 14),
    ("5540", "Plumbing and Electrical", "repairs_maintenance", "seasonal", 12),
    ("5550", "Painting and Cleaning", "repairs_maintenance", "summer_peak", 10),
    ("5560", "Landscape and Grounds", "repairs_maintenance", "growing", 12),
    ("5570", "Pest Control", "repairs_maintenance", "growing", 8),
    ("5580", "Pool and Amenity Maintenance", "repairs_maintenance", "growing", 6),
    ("5590", "Elevator Maintenance", "repairs_maintenance", "level", 4),
    ("5600", "Snow Removal", "repairs_maintenance", "winter_only", 4),
    ("5610", "Electric", "utilities", "heating_cooling", 35),
    ("5620", "Gas", "utilities", "heating", 20),
    ("5630", "Trash Removal", "utilities", "level", 25),
    ("5640", "Other Utilities", "utilities", "level", 20),
    ("5710", "Water", "water_sewer", "growing", 50),
    ("5720", "Sewer", "water_sewer", "growing", 50),
    ("5810", "Property Insurance", "insurance", "level", 70),
    ("5820", "Liability Insurance", "insurance", "level", 30),
    ("5910", "Real Estate Taxes", "real_estate_taxes", "level", 100),
    ("5950", "Ground Rent", "ground_rent", "level", 100),
    ("5990", "Other Expenses", "other_expenses", "level", 100),
]


def largest_remainder(total: int, weights: list[int]) -> list[int]:
    if total == 0:
        return [0] * len(weights)
    weight_total = sum(weights)
    if weight_total <= 0:
        weight_total = len(weights)
        weights = [1] * len(weights)
    exact = [total * w / weight_total for w in weights]
    values = [int(value // 1) for value in exact]
    remainder = total - sum(values)
    order = sorted(
        range(len(weights)),
        key=lambda i: (exact[i] - values[i], -i),
        reverse=True,
    )
    for i in order[:remainder]:
        values[i] += 1
    return values


def allocate_monthly(
    annual: int,
    profile: str,
    seed: str,
    state: str,
) -> list[int]:
    if annual == 0:
        return [0] * 12

    if profile == "heating":
        weights = [12, 12, 9, 5, 3, 2, 2, 2, 3, 5, 9, 12]
    elif profile == "cooling":
        weights = [2, 2, 3, 5, 8, 12, 14, 14, 10, 6, 3, 2]
    elif profile == "heating_cooling":
        weights = [12, 11, 8, 6, 7, 9, 12, 12, 9, 7, 7, 12]
    elif profile == "growing":
        weights = [3, 3, 5, 8, 12, 14, 14, 14, 11, 7, 5, 3]
    elif profile == "winter_only":
        if state.upper() in WARM_CLIMATE_STATES:
            weights = [0] * 12
        else:
            weights = [14, 12, 8, 0, 0, 0, 0, 0, 0, 0, 6, 14]
    elif profile == "summer_peak":
        weights = [5, 5, 7, 8, 10, 14, 16, 15, 10, 5, 3, 2]
    elif profile == "seasonal":
        weights = [8, 8, 8, 8, 8, 9, 9, 9, 9, 8, 8, 8]
    else:
        weights = [1] * 12

    if not any(weights):
        return [0] * 12

    values = largest_remainder(annual, weights)
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))
    if annual and sum(weights) > 0:
        jitter = min(annual // 200, 25)
        if jitter:
            moves = rng.sample(range(12), k=min(3, 12))
            for i in moves:
                if values[i] > jitter:
                    direction = 1 if rng.random() < 0.5 else -1
                    values[i] += direction * jitter
            difference = annual - sum(values)
            values[11] += difference
    return values


def category_accounts(category: str):
    return [account for account in CHART_OF_ACCOUNTS if account[2] == category]
