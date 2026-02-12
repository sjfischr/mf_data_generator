"""Base class for all section generators using template method pattern."""

import json
import logging
import os
from abc import ABC, abstractmethod

from lambdas.shared.models import CrosswalkData
from lambdas.shared import s3_utils, bedrock_client

logger = logging.getLogger(__name__)


class SectionGenerator(ABC):
    """Abstract base for every appraisal-section Lambda.

    Subclasses implement the four abstract methods; the ``execute`` method
    orchestrates the full generate-and-persist workflow.
    """

    def __init__(self, event: dict, context):
        self.job_id: str = event["job_id"]
        self.context = context
        self.crosswalk: CrosswalkData | None = None

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------

    def load_crosswalk_data(self) -> CrosswalkData:
        """Fetch the crosswalk JSON from S3 and validate it."""
        data = s3_utils.read_json(self.job_id, "crosswalk-data.json")
        self.crosswalk = CrosswalkData.model_validate(data)
        return self.crosswalk

    # ------------------------------------------------------------------
    # Abstract contract
    # ------------------------------------------------------------------

    @abstractmethod
    def get_section_name(self) -> str:
        """Return a slug like ``section_01_introduction``."""
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        """Return ``'haiku'``, ``'sonnet'``, or ``'opus'``."""
        ...

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system-level instruction for the LLM."""
        ...

    @abstractmethod
    def build_prompt(self, crosswalk: CrosswalkData) -> str:
        """Build the user-level prompt from crosswalk data."""
        ...

    # ------------------------------------------------------------------
    # Template workflow
    # ------------------------------------------------------------------

    def generate_content(self, prompt: str) -> str:
        """Call Bedrock with the section-specific prompts."""
        return bedrock_client.invoke_model(
            prompt=prompt,
            model=self.get_model_name(),
            system_prompt=self.get_system_prompt(),
            max_tokens=8192,
        )

    def save_output(self, content: str) -> str:
        """Persist the generated markdown to S3."""
        filename = f"sections/{self.get_section_name()}.md"
        return s3_utils.write_text(self.job_id, filename, content)

    def execute(self) -> dict:
        """Run the full generate-and-save pipeline."""
        logger.info("Generating %s for job %s", self.get_section_name(), self.job_id)
        crosswalk = self.load_crosswalk_data()
        prompt = self.build_prompt(crosswalk)
        content = self.generate_content(prompt)
        key = self.save_output(content)
        return {
            "status": "success",
            "section": self.get_section_name(),
            "s3_key": key,
        }
