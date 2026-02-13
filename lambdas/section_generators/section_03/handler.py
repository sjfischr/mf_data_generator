"""Lambda: Section 03 -- Market Analysis.

Generates a comprehensive market analysis including regional economic
overview, neighborhood analysis, multifamily supply and demand,
competitive rental analysis, and rent comparables.  Target: 6-8 pages.
"""

from __future__ import annotations

import json
import logging
import textwrap

from lambdas.shared.models import CrosswalkData
from lambdas.shared.section_generator import SectionGenerator

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class MarketAnalysisGenerator(SectionGenerator):
    """Generate Section 03 -- Market Analysis."""

    def get_section_name(self) -> str:
        return "section_03_market_analysis"

    def get_model_name(self) -> str:
        return "sonnet"

    def get_max_tokens(self) -> int:
        return 16000  # 6-8 pages requires higher token limit

    def get_system_prompt(self) -> str:
        return (
            "You are an MAI-certified commercial real estate appraiser and "
            "market analyst with 20+ years of experience writing USPAP-compliant "
            "appraisal reports for multifamily apartment properties. You have "
            "deep expertise in multifamily market dynamics, demographic analysis, "
            "and competitive market positioning. Write in formal, professional "
            "appraisal language. Output well-structured Markdown."
        )

    def build_prompt(self, crosswalk: CrosswalkData) -> str:
        pid = crosswalk.property_identification
        phys = crosswalk.property_physical
        mkt = crosswalk.market_data
        fin = crosswalk.financial_data

        # Build comparable properties summary
        comp_props = []
        for cp in mkt.comparable_properties:
            comp_props.append(
                f"  - {cp.name} | {cp.address} | {cp.units} units | "
                f"Built {cp.year_built} | {cp.occupancy}% occ | "
                f"${cp.avg_rent_per_unit:,.0f}/unit avg rent"
            )
        comp_props_text = "\n".join(comp_props)

        # Build comparable sales summary
        comp_sales = []
        for cs in mkt.comparable_sales:
            comp_sales.append(
                f"  - {cs.property} | {cs.sale_date} | "
                f"${cs.sale_price:,} | {cs.units} units | "
                f"${cs.price_per_unit:,}/unit | {cs.cap_rate}% cap"
            )
        comp_sales_text = "\n".join(comp_sales)

        # Market rents summary
        market_rents = "\n".join(
            f"  - {k}: ${v:,}/mo" for k, v in fin.market_rents_monthly.items()
        )

        return textwrap.dedent(f"""\
        Write the MARKET ANALYSIS section (Section 3) of a multifamily
        apartment appraisal report.  This is a substantial section of 6-8
        pages.

        ## Property and Market Data

        **Subject Property:**
        - Name: {pid.property_name}
        - Location: {pid.city}, {pid.state} {pid.zip}
        - County: {pid.county}
        - Units: {phys.total_units}
        - Type: {phys.building_type}
        - Year Built: {pid.year_built}

        **Submarket:** {mkt.submarket}
        - Vacancy Rate: {mkt.submarket_vacancy_rate}%
        - Rent Growth YOY: {mkt.submarket_rent_growth_yoy}%

        **Subject Occupancy:** {fin.occupancy.physical_percent}%

        **Subject Market Rents:**
        {market_rents}

        **Comparable Rental Properties:**
        {comp_props_text}

        **Comparable Sales:**
        {comp_sales_text}

        ## Required Sub-sections

        1. **Regional/MSA Overview** (1-1.5 pages)
           - Economic base and major employers
           - Population and demographic trends
           - Employment and unemployment data
           - Median household income
           - GDP and economic growth trends
           - Infrastructure and transportation

        2. **Neighborhood Analysis** (1-1.5 pages)
           - Immediate neighborhood description
           - Surrounding land uses
           - Access and transportation
           - Schools, shopping, employment centers nearby
           - Neighborhood life cycle stage (growth/stable/decline)
           - Crime statistics context
           - Planned developments or changes

        3. **Multifamily Market Overview** (1.5-2 pages)
           - Submarket definition and boundaries
           - Current inventory (units, properties)
           - Historical and current vacancy rates
           - Absorption trends
           - New construction pipeline
           - Rent trends (historical and projected)
           - Supply/demand dynamics
           - Comparison to broader MSA trends

        4. **Competitive Rental Analysis** (1.5-2 pages)
           - Detailed comparison of the comparable rental properties
           - Create a Markdown table: Property | Units | Year Built | Occ% | Avg Rent
           - Analyze each comparable's competitive position vs. subject
           - Discuss amenity differences, age, condition, location
           - Conclude on subject's competitive position

        5. **Rent Analysis & Conclusion** (1 page)
           - Market rent conclusions by unit type
           - Create a Markdown table: Unit Type | Subject In-Place | Market Rent | Premium/Discount
           - Rent growth projections
           - Concessions and incentives in the market

        6. **Market Conclusions** (0.5 page)
           - Overall market outlook
           - Risk factors
           - Impact on subject property value

        Format as professional Markdown with proper headings.
        Write approximately 4,000-5,000 words.  Use realistic but synthetic
        data that is consistent with the provided comparable data.
        """)


def handler(event, context):
    """AWS Lambda entry point."""
    gen = MarketAnalysisGenerator(event, context)
    return gen.execute()
