# Spec Delta

## Purpose

Produces a synthetic multifamily Lender Narrative as a DOCX deliverable, following the Fannie Mae DUS Transaction Approval Memo (Guide Part I, Sec 103). It documents the lender's analysis of the loan, borrower, property, market, underwriting, and risks, using only crosswalk data so every figure ties to the appraisal and workbooks.

## ADDED Requirements

### Requirement: Lender Narrative deliverable
Every successful job SHALL produce `outputs/lender_narrative.docx`. The document SHALL be titled "Lender Narrative — Transaction Approval Memo" and SHALL carry a visible notice on the cover and in the footer of every page that it is synthetic and not for lending use.

#### Scenario: Narrative produced for a successful job
- **WHEN** a generation job completes successfully
- **THEN** `outputs/lender_narrative.docx` exists for that job and opens as a valid Word document

#### Scenario: Synthetic disclaimer present
- **WHEN** the narrative is opened
- **THEN** the cover page and every page footer contain the synthetic / not-for-lending notice

### Requirement: Narrative section structure
The narrative SHALL contain exactly 17 top-level sections, in a fixed order based on the DUS Transaction Approval Memo topics, each appearing once as a top-level heading.

#### Scenario: All sections in order
- **WHEN** the narrative headings are extracted
- **THEN** these 17 headings appear exactly once, in this order:
  1. Loan Summary & Salient Facts
  2. Executive Summary & Recommendation
  3. Sources & Uses
  4. Borrower, Key Principals & Guarantor
  5. Property Management
  6. Property Description
  7. Market & Submarket Analysis
  8. Rent Roll & Occupancy Analysis
  9. Historical Operating Performance vs. Underwriting
  10. Underwritten NCF & Loan Sizing
  11. Appraisal Review
  12. Third-Party Reports
  13. Refinance Risk Analysis
  14. Strengths, Risks & Mitigants
  15. Waivers & Exceptions
  16. Conditions of Approval
  17. Underwriter Conclusion & Approval

### Requirement: Loan summary table
The Loan Summary section SHALL include a table with:
- property name and address, units
- loan purpose, execution, product, tier, tier minimum DSCR and maximum LTV
- loan amount, loan per unit
- note rate, underwriting rate basis, term, amortization, interest-only months, prepayment terms
- appraised value, underwriting value
- LTV (both bases), Underwritten DSCR, actual DSCR, debt yield, breakeven occupancy
- Underwritten NOI and NCF
- replacement reserve per unit per year, initial deposits

#### Scenario: Loan summary figures match crosswalk
- **WHEN** the Loan Summary table is read
- **THEN** each value equals the corresponding crosswalk `financing` / `operating_history` value, formatted for display

### Requirement: Figures are computed, not generated
Every number in narrative tables SHALL be rendered by code from crosswalk data. Prose sections SHALL receive the exact figures they may cite, and SHALL NOT introduce dollar amounts, ratios, or percentages that are absent from the crosswalk or from values derived from it.

#### Scenario: Prose cites only supplied figures
- **WHEN** QC extracts every dollar amount from the narrative prose
- **THEN** each amount matches a crosswalk value or a derived value within $1 rounding

### Requirement: Historical vs. underwritten comparison
The Historical Operating Performance section SHALL include a table with one row per operating-history category plus subtotals (NRI, EGI, Total OpEx, NOI, NCF), with these columns:
- `Year 3`, `Year 2`, `Year 1`, `Underwritten`
- Underwritten per unit
- Underwritten % of EGI
- variance of Underwritten vs. `Year 1`

The prose SHALL explain each category where Underwritten differs from `Year 1` by more than 5%.

#### Scenario: Comparison table ties to T-12s
- **WHEN** the comparison table's `Year 1` EGI and NOI are read
- **THEN** they equal the annual totals in `t12_year1.xlsx`

#### Scenario: Material variance explained
- **WHEN** Underwritten real estate taxes exceed `Year 1` by more than 5%
- **THEN** the section text includes an explanation for the real estate tax adjustment

### Requirement: Loan sizing presentation
The Underwritten NCF & Loan Sizing section SHALL show:
- the DSCR-constrained amount and the LTV-constrained amount
- the binding constraint
- debt service at the note rate and at the underwriting rate basis
- a DSCR sensitivity table at the note rate +100 bps and +200 bps

#### Scenario: Binding constraint stated
- **WHEN** `financing.binding_constraint` is `DSCR`
- **THEN** the section identifies DSCR as the binding constraint, and the final loan amount equals the DSCR-constrained amount rounded down to $1,000

### Requirement: Appraisal reconciliation
The Appraisal Review section SHALL compare the appraiser's pro forma (EGI, total expenses including reserves, NOI) with the lender Underwritten EGI, OpEx, NOI, and NCF. It SHALL state the appraised value, the cap rate, and the underwriting value, and explain any difference between appraisal NOI and Underwritten NCF.

#### Scenario: Appraiser vs lender NOI shown side by side
- **WHEN** the Appraisal Review table is read
- **THEN** it shows the appraiser NOI from `financial_data.net_operating_income` beside the Underwritten NOI and NCF

### Requirement: Refinance risk analysis
The Refinance Risk section SHALL project NCF from Underwritten (loan year 1) to the loan maturity year, using:
- 2% annual income growth
- 3% annual real estate tax growth
- constant economic vacancy

It SHALL report the balloon balance and the refinance DSCR at a stated refinance-rate assumption.

#### Scenario: Balloon and refinance DSCR reported
- **WHEN** the loan has a 120-month term and a 30-year amortization
- **THEN** the section reports the year-10 projected NCF, the remaining balance at month 120, and the resulting refinance DSCR

### Requirement: Strengths, risks and mitigants
The Strengths, Risks & Mitigants section SHALL list at least three strengths, and at least three risks, each risk paired with a mitigant, grounded in specific crosswalk facts (for example occupancy, submarket vacancy, sponsor experience, PCA findings, or expense ratio).

#### Scenario: Each risk has a mitigant
- **WHEN** the risks list is read
- **THEN** every risk entry has an associated mitigant

### Requirement: Narrative included in QC
QC SHALL verify that the narrative exists and contains all 17 headings. It SHALL also verify that the loan amount, Underwritten DSCR, LTV, and Underwritten NCF appear in the narrative text as formatted from the crosswalk. A missing narrative or a missing loan amount SHALL be a QC error.

#### Scenario: Missing loan amount fails QC
- **WHEN** the narrative text does not contain the formatted `financing.loan_amount`
- **THEN** QC records an error for the narrative, and the job's QC status is `FAIL`
