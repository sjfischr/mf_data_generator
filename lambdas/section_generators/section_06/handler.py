"""Lambda: Section 06 -- Sales Comparison Approach.

CRITICAL SECTION.  Generates a detailed sales comparison approach with
comparable sale analysis, adjustment grid, and reconciliation to an
indicated value.  Uses Opus for highest quality.  Target: 4-6 pages.
"""

from __future__ import annotations

import json
import logging
import textwrap

from lambdas.shared.models import CrosswalkData
from lambdas.shared.section_generator import SectionGenerator

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SalesComparisonGenerator(SectionGenerator):
    """Generate Section 06 -- Sales Comparison Approach."""

    def get_section_name(self) -> str:
        return "section_06_sales_comparison"

    def get_model_name(self) -> str:
        return "opus"

    def get_max_tokens(self) -> int:
        return 10000  # 4-6 pages requires higher token limit

    def get_tools(self) -> list:
        from lambdas.shared.agent_tools import (
            verify_sum,
            compute_price_per_unit,
            compute_valuation_metrics,
        )
        return [verify_sum, compute_price_per_unit, compute_valuation_metrics]

    def get_system_prompt(self) -> str:
        return (
            "You are an MAI-certified commercial real estate appraiser with "
            "20+ years of experience writing USPAP-compliant appraisal reports "
            "for multifamily apartment properties. You are a recognized expert "
            "in the Sales Comparison Approach, adjustment grid analysis, and "
            "paired-sales techniques. Your adjustment rationale is always "
            "well-supported by market evidence. Every number must be "
            "internally consistent and mathematically correct. "
            "Write in formal, professional appraisal language. "
            "Output well-structured Markdown."
        )

    def build_prompt(self, crosswalk: CrosswalkData) -> str:
        pid = crosswalk.property_identification
        phys = crosswalk.property_physical
        mkt = crosswalk.market_data
        val = crosswalk.valuation
        fin = crosswalk.financial_data

        # Build detailed comp sale data
        comp_sales_detail = []
        for i, cs in enumerate(mkt.comparable_sales, 1):
            comp_sales_detail.append(textwrap.dedent(f"""\
            **Comparable Sale {i}:**
            - Property: {cs.property}
            - Sale Date: {cs.sale_date}
            - Sale Price: ${cs.sale_price:,}
            - Units: {cs.units}
            - Price Per Unit: ${cs.price_per_unit:,}
            - Cap Rate: {cs.cap_rate}%
            - NOI: ${cs.noi:,}"""))
        comp_sales_text = "\n\n".join(comp_sales_detail)

        # Subject metrics
        total_sf = phys.gross_building_area_sf
        value_per_unit = val.sales_comparison_approach.value_per_unit
        value_per_sf = val.sales_comparison_approach.value_per_sf
        indicated_value = val.sales_comparison_approach.indicated_value

        return textwrap.dedent(f"""\
        Write the SALES COMPARISON APPROACH section (Section 6) of a
        multifamily apartment appraisal report.  This is a CRITICAL section
        requiring 4-6 pages of rigorous analysis.

        ## Subject Property Data
        - Property: {pid.property_name}
        - Location: {pid.address}, {pid.city}, {pid.state} {pid.zip}
        - Total Units: {phys.total_units}
        - Year Built: {pid.year_built}
        - GBA: {total_sf:,} SF
        - Building Type: {phys.building_type}
        - Stories: {phys.stories}
        - Occupancy: {fin.occupancy.physical_percent}%
        - NOI: ${fin.net_operating_income:,}

        ## Target Value Conclusion
        - Indicated Value: ${indicated_value:,}
        - Value Per Unit: ${value_per_unit:,}
        - Value Per SF: ${value_per_sf:,.2f}

        ## Comparable Sales Data
        {comp_sales_text}

        ## Required Sub-sections

        1. **Methodology** (0.5 page)
           - Describe the sales comparison approach methodology
           - Explain the search criteria used to identify comparables
           - Discuss the elements of comparison

        2. **Comparable Sale Descriptions** (1.5-2 pages)
           - For each comparable, write a detailed narrative:
             * Property description (type, units, year built, condition)
             * Transaction details (buyer, seller motivation, financing)
             * Property condition and amenities at time of sale
             * How it compares to the subject

        3. **Adjustment Grid** (1 page)
           Create a detailed Markdown table adjustment grid with these rows:
           - Sale Price
           - Price Per Unit
           - **Property Rights** (Fee Simple -- typically 0% adjustment)
           - **Financing Terms** (Cash equivalent -- typical 0%)
           - **Conditions of Sale** (Arms-length -- typical 0%)
           - **Market Conditions / Time** (adjust from sale date to effective
             date based on market appreciation)
           - Adjusted Price Per Unit (after transactional adjustments)
           - **Location** (superior/inferior/similar)
           - **Age / Condition** (based on year built and effective age)
           - **Size / Units** (economies of scale adjustment)
           - **Amenities / Quality** (amenity package comparison)
           - **Occupancy** (if materially different)
           - Net Adjustment (%)
           - Gross Adjustment (%)
           - Adjusted Price Per Unit (final)
           - Indicated Value (adjusted price per unit x subject units)

           Columns: Subject | Comp 1 | Comp 2 | Comp 3
           Show dollar and percentage adjustments.

           CRITICAL: The adjustments must reconcile so that the adjusted
           values from the comparables bracket and support the concluded
           value of ${indicated_value:,} (${value_per_unit:,}/unit).

        4. **Adjustment Rationale** (1 page)
           - Justify each adjustment category with market evidence
           - Discuss paired-sales analysis where applicable
           - Explain the magnitude and direction of each adjustment

        5. **Reconciliation** (0.5 page)
           - Discuss which comparable is most similar to the subject
           - Weight the adjusted indications
           - Conclude to an indicated value of ${indicated_value:,}
           - State value per unit of ${value_per_unit:,}
           - State value per SF of ${value_per_sf:,.2f}

        CRITICAL REQUIREMENTS:
        - All math must be correct and verifiable
        - Adjustments must be reasonable (individual < 25%, gross < 50%)
        - The grid must reconcile to the target concluded value
        - Format numbers with commas and dollar signs consistently
        - Use professional appraisal terminology throughout

        Format as professional Markdown with proper headings and tables.
        Write approximately 3,000-4,000 words.
        """)


def handler(event, context):
    """AWS Lambda entry point."""
    gen = SalesComparisonGenerator(event, context)
    return gen.execute()
