"""Lambda: Section 02 -- Property Description.

Generates a detailed property description including site description,
improvements description, unit mix details, amenities, and condition
assessment.  Includes [IMAGE: ...] placeholders.  Target: 8-10 pages.
"""

from __future__ import annotations

import json
import logging
import textwrap

from lambdas.shared.models import CrosswalkData
from lambdas.shared.section_generator import SectionGenerator

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PropertyDescriptionGenerator(SectionGenerator):
    """Generate Section 02 -- Property Description."""

    def get_section_name(self) -> str:
        return "section_02_property_description"

    def get_model_name(self) -> str:
        return "sonnet"

    def get_system_prompt(self) -> str:
        return (
            "You are an MAI-certified commercial real estate appraiser with "
            "20+ years of experience writing USPAP-compliant appraisal reports "
            "for multifamily apartment properties. You are an expert at "
            "describing physical characteristics of properties in rigorous "
            "detail. Write in formal, professional appraisal language. "
            "Output well-structured Markdown. Include [IMAGE: description] "
            "placeholders where photographs would normally appear."
        )

    def build_prompt(self, crosswalk: CrosswalkData) -> str:
        pid = crosswalk.property_identification
        phys = crosswalk.property_physical
        fin = crosswalk.financial_data

        # Build unit mix table data
        unit_mix_rows = []
        for u in phys.unit_mix:
            unit_mix_rows.append(
                f"  - {u.unit_type}: {u.count} units, "
                f"{u.avg_size_sf} SF avg, {u.total_sf} SF total, "
                f"{u.bedrooms}BR/{u.bathrooms}BA"
            )
        unit_mix_text = "\n".join(unit_mix_rows)

        amenities_text = ", ".join(phys.amenities)

        # Market rents
        market_rents = "\n".join(
            f"  - {k}: ${v:,}/mo" for k, v in fin.market_rents_monthly.items()
        )
        in_place_rents = "\n".join(
            f"  - {k}: ${v:,}/mo" for k, v in fin.in_place_rents_monthly.items()
        )

        return textwrap.dedent(f"""\
        Write the PROPERTY DESCRIPTION section (Section 2) of a multifamily
        apartment appraisal report.  This is a detailed section of 8-10 pages.

        ## Property Data

        **Identification:**
        - Property Name: {pid.property_name}
        - Address: {pid.address}, {pid.city}, {pid.state} {pid.zip}
        - County: {pid.county}
        - Year Built: {pid.year_built}
        - Effective Age: {pid.effective_age} years

        **Physical Characteristics:**
        - Total Units: {phys.total_units}
        - Total Buildings: {phys.total_buildings}
        - Building Type: {phys.building_type}
        - Stories: {phys.stories}
        - Gross Building Area: {phys.gross_building_area_sf:,} SF
        - Site Area: {phys.site_area_acres} acres ({phys.site_area_sf:,} SF)
        - Parking Spaces: {phys.parking_spaces} (ratio: {phys.parking_ratio})

        **Unit Mix:**
        {unit_mix_text}

        **Amenities:** {amenities_text}

        **Occupancy:**
        - Physical: {fin.occupancy.physical_percent}%
        - Occupied: {fin.occupancy.occupied_units} units
        - Vacant: {fin.occupancy.vacant_units} units

        **Market Rents:**
        {market_rents}

        **In-Place Rents:**
        {in_place_rents}

        ## Required Sub-sections

        1. **Site Description** -- Describe the land: shape, topography,
           zoning, utilities, access/ingress/egress, flood zone, environmental
           considerations, surrounding land uses.
           Include: [IMAGE: Aerial view of subject property site]
           Include: [IMAGE: Street view of property entrance]

        2. **Improvements Description -- Exterior** -- Construction type,
           foundation, framing, exterior finish, roofing, windows, parking
           areas, landscaping, signage.
           Include: [IMAGE: Front exterior elevation of main building]
           Include: [IMAGE: Rear exterior view showing building condition]
           Include: [IMAGE: Parking area and landscaping]

        3. **Improvements Description -- Interior** -- Common areas, hallways,
           leasing office, fitness center, pool area, laundry facilities.
           Describe finishes, flooring, fixtures, appliances.
           Include: [IMAGE: Leasing office and lobby area]
           Include: [IMAGE: Fitness center]
           Include: [IMAGE: Swimming pool and deck area]

        4. **Unit Descriptions** -- For each unit type in the mix, describe
           layout, finishes, kitchen (countertops, cabinets, appliances),
           bathrooms, flooring, HVAC, washer/dryer connections.
           Include: [IMAGE: Typical 1-bedroom unit interior - living area]
           Include: [IMAGE: Typical 1-bedroom unit interior - kitchen]
           Include: [IMAGE: Typical 2-bedroom unit interior - living area]
           Include: [IMAGE: Typical 2-bedroom unit interior - kitchen]

        5. **Unit Mix Table** -- Format the unit mix as a proper Markdown table
           with columns: Unit Type | Count | Avg SF | Total SF | BD/BA

        6. **Amenities Detail** -- Describe each amenity in detail.
           Include: [IMAGE: Community amenity area]

        7. **Condition Assessment** -- Overall condition rating (Good/Average/
           Fair), deferred maintenance items, recent capital improvements,
           remaining economic life estimate.

        8. **ADA Compliance** -- Brief statement about compliance.

        9. **Environmental** -- Phase I status, known issues.

        Format as professional Markdown with proper headings.
        Write approximately 5,000-6,000 words total.
        Include at least 12 [IMAGE: ...] placeholders throughout.
        """)


def handler(event, context):
    """AWS Lambda entry point."""
    gen = PropertyDescriptionGenerator(event, context)
    return gen.execute()
