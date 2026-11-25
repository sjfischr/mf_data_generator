# Spec Delta

## Purpose

Defines the Excel deliverables: three detailed T-12 operating statements and a unit-level rent roll. They give analysts realistic, line-item operating data that ties exactly to the crosswalk, the appraisal, and the Lender Narrative.

## ADDED Requirements

### Requirement: Three T-12 workbooks
The job SHALL produce `outputs/t12_year1.xlsx`, `outputs/t12_year2.xlsx`, and `outputs/t12_year3.xlsx`, one per `operating_history` historical period. Each SHALL be titled with the property name and its period, and its 12 month columns SHALL be labeled with actual month-year labels (for example "Nov-25") spanning that period.

#### Scenario: Month headers match the period
- **WHEN** `Year 1` spans 2025-11-01 to 2026-10-31
- **THEN** `t12_year1.xlsx` month headers read Nov-25 through Oct-26, in order

### Requirement: Detailed chart of accounts
Each T-12 SHALL present revenue, expense, and below-NOI sections with numbered GL accounts (4000 revenue, 5000 expenses, 6000 below-the-line). Each crosswalk category SHALL be expanded into realistic sub-accounts; for example, Payroll & Benefits splits into manager, leasing, and maintenance salaries, payroll taxes, workers' comp, and health benefits. Each T-12 SHALL include at least 40 detail accounts.

#### Scenario: Sub-accounts roll up to categories
- **WHEN** the annual totals of a category's sub-accounts are summed
- **THEN** the sum equals that category's amount for the period in `operating_history`

#### Scenario: Minimum detail
- **WHEN** detail (non-subtotal) account rows are counted in any T-12
- **THEN** there are at least 40

### Requirement: Subtotals and totals
Each T-12 SHALL show subtotal rows for:
- Net Rental Income
- Total Other Income
- Effective Gross Income
- each expense category
- Total Operating Expenses
- Net Operating Income
- Net Cash Flow (after replacement reserves)

Subtotals SHALL be spreadsheet formulas over the rows they summarize.

#### Scenario: Annual totals tie to crosswalk
- **WHEN** the EGI, Total Operating Expenses, NOI, and NCF annual totals of `t12_year1.xlsx` are evaluated
- **THEN** each equals the corresponding `operating_history` `Year 1` value exactly

#### Scenario: Subtotals are live
- **WHEN** a detail cell in a T-12 is edited in Excel
- **THEN** the dependent subtotals, NOI, and NCF recalculate

### Requirement: Monthly distribution with realistic seasonality
Each account's 12 monthly amounts SHALL sum exactly to its annual amount. The distribution SHALL follow account-specific seasonality:
- utilities follow heating and cooling seasons
- landscaping is concentrated in growing months
- snow removal falls only in winter months, and only for cold-climate states
- turnover / make-ready peaks in summer
- fixed contracts and accruals are level

All amounts SHALL be whole dollars, and the distribution SHALL be deterministic for a given job.

#### Scenario: Monthly amounts sum to annual
- **WHEN** any account row's 12 monthly values are summed
- **THEN** the sum equals the row's annual total

#### Scenario: Deterministic output
- **WHEN** the T-12 generator runs twice for the same job and crosswalk
- **THEN** both runs produce identical cell values

#### Scenario: No snow removal in warm climates
- **WHEN** the property state is FL, AZ, TX, CA, HI, LA, or another state classified as warm-climate
- **THEN** snow removal is zero for every month

### Requirement: Analyst columns and statistics
Each T-12 SHALL include, after the annual total:
- a Per Unit column
- a % of EGI column, for income and expense rows

Each T-12 SHALL also include monthly occupancy statistics rows: occupied units, physical occupancy %, and economic occupancy %.

#### Scenario: Per-unit column
- **WHEN** a row's Per Unit value is read
- **THEN** it equals the annual total divided by total units, rounded to whole dollars

### Requirement: Excluded items not in NOI
Non-operating items SHALL NOT appear in the revenue or operating expense sections. These include depreciation, amortization, interest, principal, owner's draw, security deposits, and insurance proceeds. Replacement reserves SHALL appear only below NOI.

#### Scenario: Reserves below NOI
- **WHEN** the T-12 rows are read in order
- **THEN** the replacement reserve row appears after the NOI row and before the NCF row

### Requirement: Rent roll consistent with crosswalk
The rent roll SHALL be dated `financial_data.effective_date` and list exactly `property_physical.total_units` units, with exactly `occupancy.occupied_units` occupied. Vacant units SHALL be distributed across the unit list rather than grouped at the end. For each unit type, the sum of in-place rents SHALL equal that type's occupied count × `in_place_rents_monthly`.

#### Scenario: Effective date not hard-coded
- **WHEN** the crosswalk effective date is 2026-11-15
- **THEN** the rent roll header reads "As of 2026-11-15", and lease dates are computed relative to that date

#### Scenario: In-place rent totals tie
- **WHEN** occupied in-place rents are summed for unit type "2BR/2BA"
- **THEN** the sum equals the occupied 2BR/2BA count × the crosswalk in-place rent for "2BR/2BA"

### Requirement: Rent roll detail columns
The rent roll SHALL include unit number, unit type, square feet, tenant name (fictitious), move-in date, lease start, lease end, market rent, in-place rent, recurring concession, security deposit, balance due, and status. It SHALL end with a totals and summary block by unit type.

#### Scenario: Summary block by unit type
- **WHEN** the rent roll summary block is read
- **THEN** it shows, per unit type, units, occupied, vacant, average market rent, and average in-place rent, plus a grand total row
