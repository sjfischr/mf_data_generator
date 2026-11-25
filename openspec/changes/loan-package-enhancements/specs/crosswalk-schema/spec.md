# Spec Delta

## Purpose

Defines the master `crosswalk-data.json` contract that every downstream stage reads, including the financing, sponsorship, third-party report, and detailed operating-history data. It also defines the arithmetic invariants that keep the appraisal, Lender Narrative, T-12s, and rent roll consistent.

## ADDED Requirements

### Requirement: Operating history columns
The crosswalk SHALL contain an `operating_history` with three historical 12-month periods (`Year 1` = most recent, then `Year 2`, `Year 3`) and one `Underwritten` column. Each historical period SHALL carry `period_start` and `period_end` dates.

#### Scenario: Periods are contiguous
- **WHEN** a crosswalk is validated
- **THEN** `Year 1.period_end` is the last day of the month before `financial_data.effective_date`
- **AND** each earlier year ends the day before the next year starts

### Requirement: Fannie Mae operating categories
Every `operating_history` column SHALL use the same category set, aligned to Fannie Mae Guide Sec 203.01 / Form 4254.DEF, with integer amounts.

#### Scenario: Category set is complete
- **WHEN** a crosswalk is validated
- **THEN** each of the four columns contains every category below, with integer amounts (zero allowed for ground rent and commercial)

| Group | Categories |
|---|---|
| Rent | GPR, loss/gain to lease, vacancy, concessions, bad debt, non-revenue units |
| Other income | laundry/vending, parking, commercial, other income |
| Expenses | real estate taxes, insurance, utilities, water & sewer, repairs & maintenance, payroll & benefits, general & administrative, marketing, professional fees, management fee, ground rent, other |
| Below NOI | replacement reserves |

### Requirement: Operating history arithmetic invariants
For every column, validation SHALL enforce:
- Net Rental Income = GPR + loss/gain to lease − vacancy − concessions − bad debt − non-revenue units
- EGI = NRI + other income categories
- Total OpEx = sum of expense categories
- NOI = EGI − Total OpEx
- NCF = NOI − replacement reserves

A violation SHALL fail validation.

#### Scenario: Expense sum mismatch rejected
- **WHEN** a column's stated total operating expenses differs from the sum of its expense categories by any amount
- **THEN** validation fails and names the column and the expected total

#### Scenario: NCF derived below NOI
- **WHEN** a valid column has NOI 1,000,000 and replacement reserves 60,000
- **THEN** its NCF is 940,000

### Requirement: Underwritten column follows Fannie Mae floors
The `Underwritten` column SHALL satisfy each of these floors:

| Item | Floor |
|---|---|
| Economic vacancy (vacancy + concessions + bad debt) | At least 5% of GPR |
| Management fee | At least 3% of EGI |
| Replacement reserves | At least $200 per unit per year |
| Real estate taxes | At least 103% of `Year 1` real estate taxes |
| Insurance | At least `Year 1` insurance |

#### Scenario: Economic vacancy floor applied
- **WHEN** `Year 1` economic vacancy is 3.1% of GPR
- **THEN** the `Underwritten` economic vacancy is at least 5.0% of the Underwritten GPR

#### Scenario: Reserve floor applied
- **WHEN** a 200-unit property is generated
- **THEN** `Underwritten` replacement reserves are at least 40,000

### Requirement: Historical summary remains available
The crosswalk SHALL continue to expose `financial_data.historical_t12` keyed `Year 1`–`Year 3`, derived from `operating_history`, with these mappings:
- `rental_income` = GPR + loss/gain to lease
- `vacancy_loss` = negative sum of vacancy, concessions, bad debt, and non-revenue units
- `other_income` = sum of other-income categories
- `operating_expenses` = Total OpEx

The appraiser pro forma (`pro_forma_income` / `pro_forma_expenses`) SHALL remain unchanged in shape.

#### Scenario: Summary ties to detail
- **WHEN** a crosswalk is validated
- **THEN** `historical_t12["Year 1"].net_operating_income` equals `operating_history` `Year 1` NOI

### Requirement: Financing terms and deterministic loan sizing
The crosswalk SHALL contain a `financing` block. The generator SHALL choose these inputs:
- loan purpose, execution, product, tier
- note rate, term, amortization, interest-only months, prepayment terms
- purchase price and date (acquisitions)

Code SHALL compute every sizing output from those inputs.

#### Scenario: Sizing outputs are computed, not generated
- **WHEN** the generator proposes a loan amount that differs from the computed sizing
- **THEN** the persisted `financing.loan_amount` equals the computed sizing, not the proposed value

### Requirement: Loan sizing method
The loan amount SHALL be the lesser of:
- (a) the DSCR-constrained amount, using Underwritten NCF, the tier minimum DSCR, and level amortizing debt service at max(note rate, underwriting rate floor);
- (b) max LTV × underwriting value.

The result SHALL be rounded down to the nearest $1,000. The underwriting value SHALL NOT exceed the appraised market value.

#### Scenario: DSCR-constrained loan
- **WHEN** NCF is 1,250,000, the minimum DSCR is 1.25, the rate basis is 6.00%, amortization is 30 years, max LTV is 80%, and the underwriting value is 25,000,000
- **THEN** the loan amount is 13,899,000 (the DSCR-constrained amount, rounded down to $1,000), because it is below 20,000,000
- **AND** `financing.binding_constraint` is `DSCR`

#### Scenario: Underwriting value capped by appraisal
- **WHEN** an acquisition's purchase price exceeds the appraised market value
- **THEN** `financing.underwriting_value` equals the appraised market value

### Requirement: Reported credit metrics
The `financing` block SHALL report, all computed:
- annual debt service at the note rate and at the underwriting rate basis
- Underwritten DSCR (NCF ÷ debt service at rate basis) and actual DSCR (NCF ÷ debt service at note rate)
- LTV against the underwriting value and against the appraised value
- debt yield (NCF ÷ loan amount), loan per unit
- breakeven occupancy ((Total OpEx + debt service at note rate) ÷ GPR)

#### Scenario: Metrics satisfy tier constraints
- **WHEN** a crosswalk is validated
- **THEN** Underwritten DSCR ≥ the tier minimum DSCR, and LTV on underwriting value ≤ the tier maximum LTV

### Requirement: Configurable tier constraints
Tier minimum DSCR, maximum LTV, and underwriting rate floors SHALL come from a single configurable table. The defaults SHALL be Conventional Fixed:

| Tier | Min DSCR | Max LTV |
|---|---|---|
| Tier 2 | 1.25 | 80% |
| Tier 3 | 1.35 | 65% |
| Tier 4 | 1.55 | 55% |

The table SHALL record its source as unverified Form 4660 values.

#### Scenario: Tier 3 selected
- **WHEN** the generator selects Tier 3
- **THEN** sizing uses a minimum DSCR of 1.35 and a maximum LTV of 65%

### Requirement: Sources and uses balance
`financing.sources_uses` SHALL list sources and uses with integer amounts whose totals are equal. Any cash to or from the borrower SHALL be the balancing item.

#### Scenario: Refinance with cash out
- **WHEN** loan proceeds exceed the payoff plus costs and reserves for a refinance
- **THEN** uses include a "Cash to Borrower" line, and total sources equal total uses

### Requirement: Sponsorship data
The crosswalk SHALL contain a `sponsorship` block, with all names fictitious:
- borrower entity name and type
- one or more key principals, each with role, years of experience, units owned, net worth, and liquidity
- guarantor
- property management company with fee percent and on-site staffing

The aggregate key-principal net worth SHALL be at least the loan amount, and aggregate liquidity at least 9 months of debt service at the note rate.

#### Scenario: Sponsor meets financial capacity
- **WHEN** a crosswalk is validated
- **THEN** the sum of key-principal net worth ≥ `financing.loan_amount`

### Requirement: Third-party report summaries
The crosswalk SHALL contain `third_party_reports`, with fictitious firm names and dates no later than the effective date:
- appraisal (firm, date, value)
- property condition assessment (firm, date, immediate repairs, 12-year reserve need)
- environmental site assessment (firm, date, finding)
- seismic (applicability, and PML if applicable)
- zoning (conformance status)

#### Scenario: Appraisal value ties
- **WHEN** a crosswalk is validated
- **THEN** `third_party_reports.appraisal.value` equals `valuation.final_value_conclusion.market_value`
