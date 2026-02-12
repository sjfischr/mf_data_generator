# Data Crosswalk Validation Rules

This document defines the consistency rules between the crosswalk-data.json
(source of truth) and all generated report sections.

## Unit Count Consistency

| Data Point | Source | Must Match In |
|---|---|---|
| total_units | crosswalk.property_physical.total_units | Section 1, Section 2, Rent Roll, Section 7 Pro Forma |
| unit_mix[].count | crosswalk.property_physical.unit_mix | Section 2 Unit Mix Table, Rent Roll, Section 7 |
| occupied_units | crosswalk.financial_data.occupancy.occupied_units | Section 7, Rent Roll |
| vacant_units | crosswalk.financial_data.occupancy.vacant_units | Section 7, Rent Roll |
| SUM(unit_mix.count) | calculated | Must equal total_units |
| occupied + vacant | calculated | Must equal total_units |

## Financial Consistency

| Data Point | Source | Must Match In |
|---|---|---|
| PGI | crosswalk.financial_data.pro_forma_income.potential_gross_income | Section 7 Pro Forma |
| EGI | crosswalk.financial_data.pro_forma_income.effective_gross_income | Section 7 Pro Forma |
| Total Expenses | crosswalk.financial_data.pro_forma_expenses.total_operating_expenses | Section 7 Pro Forma |
| NOI | crosswalk.financial_data.net_operating_income | Section 7, Section 9 |
| PGI = Rental + Other | calculated | Must reconcile |
| EGI = PGI - Vacancy | calculated | Must reconcile |
| NOI = EGI - Expenses | calculated | Must reconcile |
| Expense total = sum of line items | calculated | Must reconcile |

## Valuation Consistency

| Data Point | Source | Must Match In |
|---|---|---|
| Sales Comparison Value | crosswalk.valuation.sales_comparison_approach.indicated_value | Section 6, Section 9 |
| Income Approach Value | crosswalk.valuation.income_approach.indicated_value | Section 7, Section 9 |
| Final Market Value | crosswalk.valuation.final_value_conclusion.market_value | Section 9 |
| Cap Rate | crosswalk.valuation.income_approach.cap_rate | Section 7, Section 9 |
| Value Per Unit | crosswalk.valuation.final_value_conclusion.value_per_unit | Section 6, Section 9 |
| Cap Rate = NOI / Value | calculated | Must reconcile (within 0.05%) |
| Value/Unit = Value / Units | calculated | Must reconcile |

## Property Identification Consistency

| Data Point | Source | Must Match In |
|---|---|---|
| property_name | crosswalk.property_identification.property_name | All sections, report header |
| address | crosswalk.property_identification.address | Section 1, Section 2 |
| effective_date | crosswalk.financial_data.effective_date | Section 1, Section 9 |
| year_built | crosswalk.property_identification.year_built | Section 2, Section 6 adjustments |

## Comparable Data Consistency

| Data Point | Source | Must Match In |
|---|---|---|
| comparable_sales[] | crosswalk.market_data.comparable_sales | Section 6 (all 3 comps) |
| comparable_properties[] | crosswalk.market_data.comparable_properties | Section 3 |
| Sale prices | crosswalk.market_data.comparable_sales[].sale_price | Section 6 adjustment grid |
| Cap rates from sales | crosswalk.market_data.comparable_sales[].cap_rate | Section 7 cap rate analysis |

## T-12 / Rent Roll Consistency

| Data Point | Source | Must Match In |
|---|---|---|
| Historical NOI Year 1 | crosswalk.financial_data.historical_t12.year_1.net_operating_income | T-12 Year 1 spreadsheet |
| Historical NOI Year 2 | crosswalk.financial_data.historical_t12.year_2.net_operating_income | T-12 Year 2 spreadsheet |
| Historical NOI Year 3 | crosswalk.financial_data.historical_t12.year_3.net_operating_income | T-12 Year 3 spreadsheet |
| In-place rents | crosswalk.financial_data.in_place_rents_monthly | Rent Roll monthly rent column |
| Market rents | crosswalk.financial_data.market_rents_monthly | Rent Roll market rent column |
| Occupied unit count | From rent roll rows with status != Vacant | Must equal occupied_units |
