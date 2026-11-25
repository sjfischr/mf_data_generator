<!-- Research reference for change 'loan-package-enhancements'. Compiled 2026-11-25 from public Fannie Mae sources; verify login-gated items (Form 4660) before relying on numeric thresholds. -->

# Fannie Mae multifamily "Lender Narrative": research report for the synthetic-document feature

## 0. Summary

- **No "Lender Narrative" in the current Guide.** The online Guide has no defined term or form called "Lender Narrative". The search for "lender narrative" returned only an unrelated appraisal hit. The nearest official concepts are:
  - **Transaction Approval Memo (TAM)**, Part I, Ch 1, Sec 103.
  - **The "narrative describing the overall transaction"** required in a Pre-Review request, Part I, Ch 2, Sec 203.
  - **The legacy "DUS Underwriter's Narrative"**: Exhibit III-2 of the older Guide, and Form 4605 for the Small Loan product.
- **Best template for the spec.** The legacy Exhibit III-2 and Form 4605 are the only official Fannie Mae documents that give an ordered outline. Both are legacy. Treat them as structure and content guidance, not current requirements.
- **Current requirements** are spread across Part I Sec 103, Part II Sec 201–206 and Sec 401–406, and Part IV. They define what the memo must address and document.
- **T-12 categories** are well defined by two official sources. Guide Sec 203.01 (Underwritten NCF table) is current and fetchable. Form 4254.DEF (Aug 2024) is also current and fetchable.
- **Access.** The online Guide is publicly fetchable, with a few pages login-gated. The current Form 4660 page (https://mfguide.fanniemae.com/node/17936) returned only a login banner. Tier/DSCR/LTV numbers below come from a Nov 2023 Form 4660 redline PDF, so verify them before hard-coding.

---

## 1. What it is, where it's required, who prepares it, when it's submitted

### Verified from official sources

| Item | Finding | Source |
|---|---|---|
| Closest current concept | The **Transaction Approval Memo** must "document your analysis of all reasonably identifiable strengths and weaknesses of the proposed Mortgage Loan transaction, and all due diligence findings required by the Guide", and must "address and mitigate" the topics listed below. | https://mfguide.fanniemae.com/node/10726 (Part I, Ch 1, **Section 103**) |
| TAM topics (Sec 103) | (1) Property financial performance, trends, value; (2) current and expected physical condition over the loan term; (3) environmental conditions and seismic risk; (4) ability to refinance at maturity; (5) Borrower, Key Principal and Guarantor financial capacity and experience; (6) Property market performance and trends; (7) any other factors that could affect the transaction during the term or at maturity; (8) analysis and support for decisions on any matter covered in Parts I–III. Guidance: Fannie Mae considers "the quality and thoroughness of your analysis, and the appropriateness and quantity of adjustments". | same |
| Pre-Review narrative | A Pre-Review request via DUS Gateway must include, at a minimum, "a preliminary loan-sizing spreadsheet with the preliminary Underwritten NCF and a refinance risk analysis" and "**a narrative describing the overall transaction, including risks and mitigating factors for each Pre-Review reason**". It must also include "any additional information requested by Fannie Mae" and category-specific items. | https://mfguide.fanniemae.com/node/10676 (Part I, Ch 2, **Section 203**) |
| Who prepares | The Lender (DUS Lender). The Chief Underwriter, or a delegated employee directly supervised by the Chief Underwriter, must review and approve all supporting material before a Pre-Review submission. | same; Part I Ch 1 Sec 102 https://mfguide.fanniemae.com/node/10716 |
| When submitted: Pre-Review | Before Rate Lock, via DUS Gateway, for loans that are not fully delegated. | node/10676 |
| When submitted: delegated | A fully delegated loan is underwritten to Form 4660, Parts I–III and the product chapters. The TAM is part of the Mortgage Loan Delivery Package. | node/10716; node/13256 |
| When submitted: delivery | The Streamlined Rate Lock chapter states the final Delivery Package must include "a complete Transaction Approval Memo; underwriting spreadsheets…; … and all required full underwriting documentation" (Part IV, Ch 3, **Sec 306.02**). | https://mfguide.fanniemae.com/node/13256 |
| Delivery mechanics | The delivery package follows the Delivery Package Table of Contents (Form **6502** Folder I/III, Folder II). Loan data goes into C&D by the Delivery deadline, per Part IV, Ch 4, **Sec 402.01**. The Form 6502 listing includes the "Underwriting Certification (6460 series), with all attachments". | https://mfguide.fanniemae.com/node/2706 ; https://mfguide.fanniemae.com/node/13486 ; https://multifamily.fanniemae.com/sites/mf/files/migrated-files/content/legal_form/6502.docx |
| Registration | Every loan is registered in DUS Gateway, with the Multifamily Affordability Estimator (MAE) submitted at the earlier of a pricing quote or application (Part I, Ch 2, **Sec 201**). | https://mfguide.fanniemae.com/node/10816 |

### TAM documentation hooks scattered through the Guide

Each of these is a section the generator can cite in a "Due Diligence Findings" subsection. All were fetched from https://mfguide.fanniemae.com/node/<id>:

- **Sec 202.02F, Lender Appraisal Review** (node/21566): the appraisal review is documented in the TAM.
- **Sec 202.02G, Subsequent Appraisals** (node/21571): documented in the TAM.
- **Sec 202.03B, Property's Ownership History** (node/21586):
  - Analyze 3 years of financing and sale history.
  - For an acquisition within 24 months, document the circumstances of the sale and support any increased value.
  - Investigate any PSA vs. public-record price discrepancy.
- **Sec 203.01**, Underwritten NCF: document and reconcile each adjusted historical line item and provide supporting detail in the TAM (node/7531).
- **Sec 205, Cash Out Analysis** (node/10791): document hard equity remaining, hold period, effective age and condition, and NCF vs. cap-rate-driven value change.
- **Sec 206, Borrower Business Plan** (node/21596): documented in the TAM.
- **Sec 401.01 and 401.03, Lease Audit**: summarize results, including rent-collection validation, bad debt and secondary income (node/22171, node/22181).
- **Sec 402.02, Capital Item Replacements** (node/22211): documented in the TAM.
- **Sec 505.03, Seismic** (node/4626).
- **Sec 301.03, Legal Non-Conforming** (node/3196).
- **Sec 101, Eligible Properties**: internet search for negative press, justified in the TAM (node/3116).
- **Sec 307.02, Brokered Transaction Certifications**.
- **Sec 312.02A, Conflict Mortgage Loans**.

### Legacy "Underwriter's Narrative"

- **Exhibit III-2 "Underwriter's Narrative"** (legacy DUS Guide; file metadata date 2003-11-06). It states the narrative "must discuss all of the material reviewed and each of the decisions made by the Lender in underwriting the Mortgage… Particular emphasis should be placed on any decision made… with respect to unusual or aggressive elements of the transaction." URL: https://multifamily.fanniemae.com/sites/mf/files/migrated-files/content/guide_form/e_iii.2.doc
  - It references the old Part III numbering (e.g., "Section 310 Replacement Reserves", "Section 409 Overall Underwriting Conclusions"). Do not cite those numbers as current.
- **Form 4605 "DUS Underwriter's Narrative for Small Loan Product"** (legacy .doc; example years in the template are 1995–1998). It is a checkbox and rating-scale form for the Small Loan product. URL: https://multifamily.fanniemae.com/sites/mf/files/migrated-files/content/guide_form/4605.doc

---

## 2. Structure

### A. Legacy Exhibit III-2: 17 required discussion areas (official, legacy)

Source for all of this section: the Exhibit III-2 URL above. Verified by extracting the document text.

1. **Borrower, Key Principals, Principals.**
   - Borrower structure, including tiered partnerships, foreign investors and trusts.
   - Experience, and justification for any bankruptcy, default or foreclosure history.
   - Acquisition rationale, capacity and willingness to support the Property.
   - Payment history, and the Fannie Mae experience check (formerly MORNET).
   - Conclusion on creditworthiness, experience, capacity, attitude and motivation.
2. **Each Key Principal.**
   - Rationale for selection and experience.
   - Net worth and liquidity, with the amount verified and the verification method.
   - Performance of owned properties.
   - Competing demands and liabilities (properties at a deficit, contingent liabilities, upcoming refinancings, lawsuits).
   - Credit and public-records search, and a conclusion.
3. **Each Principal.** Credit and public records, experience, character, and verification of financial statements if needed.
4. **Property Management.**
   - Company activity and experience.
   - Management fee, staffing adequacy, salaries and benefits.
   - Shared costs, and any planned management change with its cost estimate.
   - Conclusion on adequacy.
5. **Market.**
   - Lender's and appraiser's opinion of the market, employers, unemployment, population and demographics.
   - Area vacancy and absorption, rent levels and trends, concessions, and new construction.
   - Depth of the market and any Lender/appraiser divergence.
   - Loan concentration.
6. **Neighborhood.** Development prospects, competition, access to employment, retail, schools and transit, and negative influences.
7. **Tenant Base.** Tenant type, competition (including homeownership), and special-tenancy compliance (student, military).
8. **Site.** Description, access, easements and encroachments, flood and seismic zones, and phased development.
9. **Zoning.** Compliance, and a threshold evaluation if applicable.
10. **Property Improvements and Marketability.**
    - Age, construction and unit mix.
    - Planned improvements and electrical adequacy.
    - Moderate Rehab / Recently Completed reports.
    - Marketability vs. competitors.
11. **Physical Needs Assessment.** Quality, immediate repairs, deferred maintenance, and the Completion/Repair Agreement.
12. **Replacement Reserves.** Amount determination, funding schedule, reasonableness of the schedule, and justification of any waiver.
13. **Environmental.** Report quality, Phase I/II results, and the O&M plan.
14. **Appraisal.**
    - Compliance, including the standards then in force (vacancy ≥5%, reserves ≥$150; these legacy figures are now superseded).
    - Market survey, sales comps and adjustments.
    - Income estimate vs. comps, concessions netted, and expense line items.
    - Cap rate and band of investment.
    - 3-year sale reconciliation, and the underwriting value vs. appraised value.
15. **Loan Amount Calculations.**
    - Income method, other income, and economic vacancy.
    - EGI vs. prior-year EGI, expense line-item justification, and NOI vs. prior-year NOI.
    - Applicable Tier DSCR and LTV, and any adjustments.
16. **Lender Waivers.** Rationale for each waiver, with copies of any Fannie Mae-granted waivers.
17. **Chief Underwriter's Analysis and Conclusions.**
    - Strengths and weaknesses.
    - Market depth.
    - Borrower strength, plus **sources and uses**, with any cash-out justified.
    - Property condition and reserves.
    - Competitiveness.
    - **Refinance prospects at maturity**, with projections and assumptions. Considering a shorter amortization or fully amortizing structure is a legacy item.
    - Recommended combination of DSCR, economic vacancy and reserves, and the rationale for any loan above the base amount.

### B. Form 4605 (Small Loan) section order (official, legacy)

Header: Lender, Date, Loan Officer, Underwriter, Property Inspection Date.

1. **Salient Facts & Loan Features.**
   - Mortgage identification: commitment number and date, property, borrower, key principals and principals.
   - Loan information: units, loan amount per unit, underwriting value, appraised value, purchase price and date, LTV (underwriting and appraised), DSC, underwritten NOI, income available for debt service, replacement reserve, initial reserve, repair escrow, other escrows, break-even.
   - Conditions of approval.
   - Structure and execution (Cash/MBS/Credit Enhancement; DUS/Prior Approval), LIHTC, pass-through rate, guarantee fee, servicing fee, note rate.
   - Interest-only, fixed or ARM; term, amortization, yield maintenance.
   - Pricing Tier and Underwriting Tier; Special Risk Category.
   - Minimum DSC and maximum LTV for the Tier; Base vs. Maximum Loan; loan purpose.
   - Waivers granted or requested.
2. **Executive Summary / Risk Assessment.** Property history; strengths and weaknesses of ownership, management, market and submarket, neighborhood, and site/physical plant; secondary financing; exit strategy; special considerations; "is this loan eligible for the proposed Tier?"
3. **Sources and Uses of Funds.**
   - Sources: DUS loan and secondary financing.
   - Uses: existing mortgage(s) or purchase price, origination fees, closing costs, replacement reserves, completion/repairs, other, and cash from/to Borrower.
   - Total uses = total financing.
4. **Borrower, Key Principals, and Principals.**
   - Ownership table and organization data.
   - Experience check, credit report and public-records dates.
   - Borrower and Key Principal financial statements, net worth, REO schedule ("Schedule A"), lawsuits, contingent liabilities and upcoming refinances.
5. **Property Management.** Management entity and fee % of EGI, staffing and salary table, adequacy rating, and lease questions (short-term, corporate, Section 8, commercial, restrictions, lease audit % reviewed).
6. **Market Description.** Population; 1–5 ratings for economic strength, projected strength, employment diversification, demand volatility, competitive supply and future development; vacancy trend; tenant profile (% student, military, family, elderly).
7. **Neighborhood Data.**
8. **Site, Improvements and Marketability.**
   - Site data, utilities, building data and unit mix table (count, BR, BA, SF, underwritten rent).
   - Appliances, unit amenities, utilities and who pays, security features, common amenities.
9. **Physical Needs Assessment (PNA).**
10. **Environmental Site Assessment.**
11. **Appraisal.** Documents included, market and income approach checks, cap rate checks, final value, and Lender's conclusions (underwriting value and cap rate).
12. **Financial Analysis and Loan Calculations.**
    - Schedules: C (Small Loan UW spreadsheet), E (rent roll turnover), F (historical vacancy).
    - GPI method, and vacancy, bad debt and concessions justification.
    - Other income: commercial, laundry, parking, ancillary.
    - Expense section with nine categories, each showing 3 prior years, YTD, budget, appraiser and underwriting figures: (1) Management, (2) Administration, (3) Payroll, (4) Utilities, (5) Water & Sewer, (6) Repair & Maintenance, (7) Insurance, (8) Real Estate Taxes, (9) Total.
13. **Approval.** Loan Committee approval, and Chief Underwriter and Chief Loan Officer sign-off.

### C. Current Guide: what the memo must demonstrate

This is a synthesis from the Guide sections above, not a published outline. Verified in the sense that the underlying sections exist, but the ordering is mine.

- Transaction summary and loan terms.
- Sources and uses, plus cash-out analysis (Sec 205).
- Ownership and acquisition history (Sec 202.03B).
- Borrower, Key Principal, Principal and Guarantor analysis (Part I Ch 3, Sec 301–312). The Ch 3 section list: 301 Generally; 302 Borrower Organizational Structure; 303 Key Principals; 304 Limited Experienced Owner; 305 Financial Statements; 306 SREO (Form 4526); 307 Certifications (Form 6460); 309 Applicant Experience Check.
- Property management (Part II Ch 1 Sec 114).
- Market analysis (Sec 201), with strengths and weaknesses "using objective factors".
- Appraisal review (Sec 202.02F) and appraised vs. underwriting value (Sec 202.03).
- Income analysis (Sec 203.01–.02) and refinance risk (Sec 204).
- Lease audit and collections (Sec 401).
- Site inspection (Sec 402).
- PCA (Sec 404; Form 4099) and completion/repairs (Sec 405).
- Replacement reserves (Sec 406) and tax/insurance escrows (Sec 407).
- Legal and zoning (Part II Ch 3 Sec 301–306).
- Insurance, environmental and seismic (Part II Ch 5 Sec 501–506).
- Business plan if a renovation is planned (Sec 206).
- Waivers (Pre-Review, Part I Ch 2 Sec 203).
- Overall conclusion and recommendation, and approval.

### D. Official vs. industry practice

| Section | Status |
|---|---|
| Items in Sec 103 topic list, Exhibit III-2 and Form 4605 | Official (current / legacy as labeled) |
| Pre-Review "risks and mitigating factors for each Pre-Review reason" | Official, current |
| Rating scales (1–5), "Strengths/Weaknesses" blocks | Official, Form 4605 (legacy) |
| Section ordering for a modern DOCX; "Recommendation" heading; DSCR sensitivity; debt yield; breakeven occupancy | **Inferred / industry convention** (see below) |

Debt yield is not a Fannie Mae Tier metric in anything I found. Break-even appears only in the Form 4605 header ("Break-even $"). The Form 4660 expense-ratio test (50% or less) appears only as an underwriting floor condition. Treat any field beyond those as the feature's own design.

---

## 3. Key data fields and calculations

All verified against the Guide unless marked **(inferred)**.

**Underwritten NCF** (Sec 203.01, node/7531). The table is shown condensed here:

- Gross Rental Income = actual rent for occupied units plus market rent for vacant units, from the current rent roll × 12.
- Plus rents on non-revenue units that were expensed (models, employees) = **GPR**.
- Minus premiums and corporate premiums, physical vacancy, concessions and bad debt = **NRI**.
  - **Economic vacancy rule:** vacancy + concessions + bad debt = the **greater** of (a) the shortfall of annualized trailing-3-month net rental collections vs. GPR, and (b) **5% of GPR**.
  - **NRI trend test:** if the trailing-3-month NRI is more than 2% below the trailing-6 or trailing-12 NRI, adjust NRI down to 2% below the lowest of the trailing 1/3/6/12-month figures. The adjustment is a minimum of 2%.
  - NRI may exceed the trailing-3-month figure only if rents are stable or increasing, and it cannot exceed the highest 1-month NRI within that period.
- Plus other income. It must be stable, common in the market, non-recurring items excluded and supported by prior years. Items:
  - Commercial income, less 10% vacancy; net commercial is capped at 20% of EGI.
  - Short-term-rental income and parking.
  - Premiums and corporate premiums (corporate premiums are limited to 10% of units).
  - Laundry and vending.
  - Residential parking and all other income.
  - = **EGI**.
- Minus operating expenses, line by line, then minus condo/shared-use assessments and ground rent = **Underwritten NOI**.
- Minus a Replacement Reserve of at least **$200 per unit** per year, "whether the escrow is funded or not" = **Underwritten NCF**.
- Management fee is the greatest of 3% of EGI (2.5% is allowed only under specific conditions), the actual fee, or the appraiser's market fee.
- Real estate taxes are the greatest of the actual future bill or 103% of the prior year, with special rules for California, abatements and reassessment.
- Insurance is the quoted premium, or 105–110% of the current premium for policies close to expiring. For an acquisition, use the purchaser's carrier.

**Underwritten DSCR** (Sec 203.02, node/10786). Underwritten NCF ÷ annual level debt service, using the **greater of the actual note rate and the Underwriting Interest Rate Floor** per Form 4660 on the actual amortization. For loans with an interest-only period, use the same level amortizing payment regardless of the IO period.

**Underwriting Value** (Sec 202.03C, node/7516). It cannot exceed the Appraised Value. If acquired less than 12 months before the Commitment Date, it cannot exceed the lower of the appraised value and (acquisition price plus completed or escrowed value-add capital).

**Refinance risk** (Sec 204.01, node/7556). Loan Year 1 equals the Underwritten NCF. After that:
- Income growth uses the DUS Gateway-published rates for the property (2% for structured or multi-property deals).
- Economic vacancy stays at the underwritten rate.
- Real estate taxes follow DUS Gateway rates (3% for structured or multi-property deals). California: 2% for acquisitions; for refinances no trending until the actual bill would exceed the underwritten tax.
- Alternative assumptions are needed if the base assumptions are inadequate (Sec 204.02, node/7561).

**Tier minimums and floors** (source: Form 4660, Nov 2023 redline; likely outdated, so verify against the current Form 4660):

- Source: https://mfguide.fanniemae.com/system/files/11-06-23-01-00-32-PM/Form%204660%20%28redline%29.pdf (pp. 17–24).
- **Conventional fixed / hybrid ARM:**

| Tier | Min DSCR | Max LTV |
|---|---|---|
| Tier 2 | 1.25 | 80% |
| Tier 3 | 1.35 | 65% |
| Tier 4 | 1.55 | 55% |

- Conventional ARM: 1.00 / 1.10 / 1.30, with the same LTVs.
- Small Mortgage Loan (fixed): same as conventional fixed.
- Student housing (fixed): 1.30 / 75% for Tier 2.
- Seniors, MAH and military each have their own rows.
- **Tier 2 adjustments:** reduce LTV by 5% for cash-out (more than 12 months since acquisition, with exceptions); reduce LTV by 5% if the term is under 84 months; DSCR amortization must not exceed 30 years.
- **Underwriting interest-rate floors, fixed rate, "all other" loans:**

| Term (months) | Tier 2 |
|---|---|
| < 84 | 6.75% (4.25% for qualifying Strong-Market loans with expense ratio ≤50%) |
| 84–119 | 5.50% |
| 120–143 | 5.00% |

  - Tiers 3 and 4 have no floor.

**Fields a synthetic narrative should surface:**

- *Verified:*
  - Loan amount, per unit, UW value, appraised value, purchase price/date.
  - LTV vs. UW value and vs. appraised value.
  - Underwritten NOI, NCF, DSCR, and the DSCR basis (note rate vs. floor).
  - Tier, loan type (Base or Maximum), purpose, rate, term, amortization, IO, pass-through, guarantee and servicing fees, prepayment.
  - Reserves: monthly replacement reserve, initial reserve, repair escrow, other escrows.
  - Expense ratio, management fee % of EGI, economic vacancy, physical occupancy.
  - Conditions of approval, waivers.
- *Inferred (industry convention, not found in a Fannie Mae source):* debt yield (NCF ÷ loan), breakeven occupancy as a computed field, DSCR sensitivity, per-unit expense metrics, and a "Recommendation" heading. Break-even appears only as a label in Form 4605.

---

## 4. Operating statement categories and forms

### Related forms (verified by name in the Guide)

| Form | Purpose | Source |
|---|---|---|
| **4660** | Multifamily Underwriting Standards (Tier DSCR/LTV, floors, Pre-Review categories) | https://mfguide.fanniemae.com/node/2721 |
| **4254 / 4254.Seniors** | Quarterly and annual **Financial Analysis of Operations** (servicing-side, via MAMP) | Part V Ch 5 Sec 503.01, https://mfguide.fanniemae.com/node/18136 |
| **4254.DEF** | Line-item definitions for Form 4254 (**Aug 2024**) | https://multifamily.fanniemae.com/media/35991/display |
| **4099** | PCA | Sec 406.01, node/4106 |
| **4827** | Instructions for Appraisers | Sec 202.03A, node/7511 |
| **4526** | Schedule of Real Estate Owned (SREO) | Part I Ch 3 Sec 306 (TOC) |
| **6460** | Multifamily Underwriting Certificate | Sec 307.01 (TOC) |
| **6502** | Delivery Package Table of Contents | node/2706 |
| **4093** | Seismic Risk Assessment Data Supplement | Search snippet for Sec 505.02 (node/4621) |
| **4605** | Legacy Underwriter's Narrative, Small Loan | URL in Section 1 |

**Correction to the question's guesses:** Form **4254** (Financial Analysis of Operations) is the relevant operating-statement form. I found no "Form 6101 Operating Statement" and no "Multifamily Underwriting Template" form number. Form 4254 is a **servicing** form, but its line-item taxonomy mirrors the underwriting categories.

### Official category set (Sec 203.01 and Form 4254.DEF)

All items are verbatim from the sources. The two align closely.

**Income**

- **Gross Potential Rent (GPR).**
  - Includes non-revenue units (model, office, employee, maintenance).
  - Gain/loss to lease and lease differential are added or subtracted here.
  - Rent-loss insurance is included.
  - Rent Loss, Past Tenants Rent and Prepaid Rent appear in "Borrower Actual" but are removed from "Normalized".
- **Less Vacancy Loss.** Residential only. Non-revenue units are not counted as vacancy; they are expensed in Payroll or G&A.
- **Less Bad Debt.**
- **Less Concessions.**
- **Laundry/Vending.**
- **Parking.**
- **Commercial Income** (net of vacancy).
- **Other Income:**

| Other Income: include | Other Income: omit |
|---|---|
| Application fees | Corporate tax/refunds |
| Cable income | Delinquency / ending delinquency |
| Club house rental | FASB 13 straight-line lease income |
| Late fees | Gain on sale |
| NSF fees | Insurance proceeds (rent-loss goes to GPR) |
| Pet income | Interest income |
| Premiums | Mobile home sales |
| Reimbursements | Partnership funds received |
| Storage income | Sales tax collected |
| Temporary tenants | Security deposits collected/returned/interest |
| Utility income (RUBS) | Tax reimbursement (prior period) |
| Forfeited security deposits | Rate cap agreement funds received |
| Misc | Past tenants rent / prepaid rent |
| Non-refundable fees | |
| IRP (affordable) | |
| Co-op flip fees / unit sales (co-ops only) | |

- **EGI** (auto-calculated).
- Also reported: physical occupancy % (a tenant must hold a lease of at least 6 months, physically occupy the unit and pay rent; non-revenue units count as occupied), occupancy date, and economic vacancy %.

**Expenses**

| Category | Sample items included (Form 4254.DEF / Sec 203.01) |
|---|---|
| **Management Fees** | Property management fee; asset management fee if it relates to operations. Must be at least 3% of EGI, with exceptions. |
| **General & Administrative** | Admin fees, ad valorem tax, alarm, answering service, applicant screening, auto, bank charges, broker/leasing commissions, licenses and permits, cell phones, computer, courtesy patrol, credit check, donations, education, equipment leases, eviction expense, life safety, mileage, model apartment, office unit (non-revenue), office supplies, postage, printing, security, telephone, travel, uniforms, vehicles, and others |
| **Payroll & Benefits** | 401(k), bonuses, contract labor (make ready, carpet cleaning), employee insurance, FICA/FUTA/SUTA, manager/leasing/maintenance salaries, payroll processing, temporary help, unemployment, workers' comp |
| **Utilities** | Building lights, dumpster rental, electricity, fuel oil, heat, gas, non-CAM electric, parking lot electric, trash removal, vacant-unit utilities |
| **Water & Sewer** | Water, sewer, septic |
| **Advertising & Marketing** | Apartment finder, banners, brochures, signage, finder's fees, media, newspaper, promotions, resident relations, supplies |
| **Professional Fees** | Accounting/audit, architectural, attorney/legal, bookkeeping, engineering, tax preparation |
| **Ground Rent** | Ground rent or land lease payments (Form 4254.DEF; Sec 203.01 item 19) |
| **Repairs & Maintenance** | Appliance, building, carpet, cleaning, CAM, decorating, electrical, elevator, exterminating, HVAC, janitorial, landscaping, locks/keys, make ready, mechanical, painting (turnover), parking lot, pest control, plumbing, pool, snow removal, supplies, turnover, vacancy prep, irrigation, window coverings (minor) |
| **Property Insurance** | All property insurance: fire, boiler, windstorm, earthquake, flood, and liability |
| **Real Estate Taxes** | Excluding delinquent taxes or prior-year credits |
| **Other Expenses** | Ancillary, general building, miscellaneous, other costs |
| **Condo/Shared-use assessments** | Only if applicable (Sec 203.01 item 18) |

- Sec 203.01 groups some lines differently than Form 4254.DEF. It places Real Estate Taxes and Insurance as separate items (17(b), 17(c)), Ground Rent as item 19 and condo fees as item 18, and puts Ad Valorem tax under G&A.
- **Omit from all expense categories:** amortization, depreciation, entity fees, financing fees, interest, legal fees associated with securing the mortgage loan, life insurance, owner's draw, partnership fees, principal payments, sales tax paid, trust account fees, upfront rate cap costs.

**Below NOI**

- **Capital Expenditures (Replacement Reserve):**
  - Normalized = the greater of the underwritten reserve and the actual required contribution.
  - If the underwritten value is unavailable and the reserve is waived, use $250/unit (non-senior) or $300/unit (senior).
  - The Sec 203.01 underwriting minimum is $200/unit.
- **Extraordinary Capex:** FF&E reserve, repair escrow, and capital items not funded from the Replacement Reserve.
- **NCF** = NOI − Replacement Reserve.
- **Debt service:** A-note (first lien), B-note (second lien and supplementals).

**Other helpful definitions from the Guide:**

- Under Sec 203.01, items classified as capital rather than R&M (carpet and appliance replacement at turnover) are excluded from operating expenses. Form 4254.DEF gives the same R&M / Capex rule.
- Sec 401.03 requires validating collections via a cash ledger, receipts journal or bank statements, and validating secondary income (RUBS, cable, laundry, parking).
- The 20%-variance commentary rule applies to servicing (Sec 503.01), not underwriting.

### Suggested synthetic T-12 chart of accounts (design proposal, inferred)

The category names, order and groupings below come from the official lists above. The individual account numbers and sub-account names are my own illustrative additions.

```
4000 REVENUE
 4010 Gross Potential Rent (market)           [GPR]
 4020 Gain/Loss to Lease                      [adj to GPR]
 4030 Vacancy Loss                            [Vacancy]
 4040 Model/Employee/Non-revenue units        [GPR add / expense per Sec 203.01 item 2]
 4050 Concessions                             [Concessions]
 4060 Bad Debt / Write-offs                   [Bad Debt]
 4100 Laundry / Vending                       [Laundry]
 4110 Parking / Garage                        [Parking]
 4120 Commercial Income                       [Commercial]
 4130 Other Income: Late Fees, NSF, Application Fees, Pet Fees/Rent, Storage,
      RUBS/Utility Reimb., Cable/Bulk Internet, Forfeited Deposits,
      Non-refundable Fees, Clubhouse Rental, Misc.   [Other Income]
 4900 Excluded (map to "omit"): Interest income, Security deposits, Insurance proceeds, Gain on sale
 = EFFECTIVE GROSS INCOME

5000 OPERATING EXPENSES
 5010 Management Fee                          [Management]
 5100 Payroll & Benefits (Mgr, Leasing, Maint salaries, Payroll taxes, Workers' comp, Health)
 5200 General & Administrative (Office, Telephone, Leasing/Screening, Security, Licenses, Eviction, Postage)
 5300 Advertising & Marketing
 5400 Professional Fees (Legal, Accounting, Bookkeeping, Tax prep)
 5500 Repairs & Maintenance (R&M Supplies, Turnover/Make-Ready, Contract Services:
      Landscape, Pest, Elevator, Pool, Snow, Janitorial, HVAC/Plumbing repairs)
 5600 Utilities (Electric, Gas, Trash)
 5610 Water & Sewer
 5700 Insurance (Property, Liability)
 5800 Real Estate Taxes
 5900 Ground Rent (if leasehold)
 5950 Other Expenses
 = TOTAL OPERATING EXPENSES
 = NET OPERATING INCOME

6000 BELOW-THE-LINE (excluded from NOI)
 6010 Capex / Replacement Reserve deposits
 6020 Extraordinary Capex
 6100 Excluded items: Depreciation, Amortization, Interest, Principal, Owner's draw, Entity fees, Financing fees
```

For the T-12 comparison table, show actual vs. underwritten per line and per unit, with variance %.

---

## 5. Gaps and uncertainties

- **Terminology.** The term "Lender Narrative" is not defined in the current Guide. The feature should present its output as a "Transaction Approval Memo / Lender Narrative" and note that the structure is an informed synthesis.
- **Current Form 4660** (node/17936) is login-gated. Tier and floor numbers above come from the Nov 2023 redline and may be superseded. Pre-Review categories and market definitions have likely changed.
- **Legacy outline.** Exhibit III-2 and Form 4605 were extracted from legacy binary .doc files. They are very old (Form 4605 template years 1995–1998); their numeric standards (5% vacancy floor, $150 reserves) are superseded by Sec 203.01 (≥5% economic vacancy test and $200/unit reserve).
- **The Pre-Review table** (Sec 203, node/10676) lists category-specific items. I read only the first part: Credit Facility, Crowdfunding Equity, DST, Forward Commitment and Near Stabilized.
- **DUS Gateway** specifics (field-level submission requirements, the loan-sizing spreadsheet template) were not found publicly. Only the existence of Deal Documents and Loan Option templates is confirmed (https://multifamily.fanniemae.com/applications-technology/dus-gateway).
- **Not found / unverified:**
  - No official Fannie Mae "Lender Narrative Template" job aid.
  - No form named "Underwriting/Operating Statement analysis" or "Form 6101".
  - Seismic form number (4093) is from a search snippet only.
  - The legacy 1998 Form 4254 field list (https://multifamily.fanniemae.com/sites/mf/files/migrated-files/content/legal_form/v-7.pdf) was seen only as a truncated search snippet.
  - Sec 203.01 expense items 17(a)–17(k) were read in full, but the exact order of Form 4254 lines in the current MAMP template was not seen, only the .DEF definitions.
- **Suggested follow-up.** Check the login-gated Form 4660 (current), the Form 6502 contents list (already downloaded; 72 KB docx at https://multifamily.fanniemae.com/sites/mf/files/migrated-files/content/legal_form/6502.docx) for the underwriting file contents, and Form 4254.Seniors only if seniors housing is in scope.
