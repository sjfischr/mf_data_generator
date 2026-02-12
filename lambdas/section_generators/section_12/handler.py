"""Section 12: Addenda (Haiku)."""

import logging

from lambdas.shared.models import CrosswalkData
from lambdas.shared.section_generator import SectionGenerator

logger = logging.getLogger(__name__)


class Section12Addenda(SectionGenerator):
    def get_section_name(self) -> str:
        return "section_12_addenda"

    def get_model_name(self) -> str:
        return "haiku"

    def get_system_prompt(self) -> str:
        return (
            "You are an MAI-certified commercial appraiser writing the Addenda "
            "section of a multifamily appraisal report. List all supporting "
            "documents and exhibits included in the appraisal package."
        )

    def build_prompt(self, crosswalk: CrosswalkData) -> str:
        prop = crosswalk.property_identification
        phys = crosswalk.property_physical

        return f"""Write Section 12: Addenda for the appraisal of {prop.property_name}
located at {prop.address}, {prop.city}, {prop.state} {prop.zip}.

Property: {phys.total_units}-unit {phys.building_type} multifamily complex

List the following addenda items:
- Addendum A: Subject Property Photographs
- Addendum B: Aerial/Location Maps
- Addendum C: Tax Assessment Data
- Addendum D: Rent Roll (as of effective date)
- Addendum E: Historical Operating Statements (T-12, 3 years)
- Addendum F: Comparable Rental Data Sheets
- Addendum G: Comparable Sales Data Sheets
- Addendum H: Engagement Letter
- Addendum I: Appraiser Qualifications

For each addendum, include a brief 1-2 sentence description of what it contains.
Output approximately 1 page of content in markdown."""


def handler(event, context):
    return Section12Addenda(event, context).execute()
