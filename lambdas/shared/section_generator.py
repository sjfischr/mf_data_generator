"""Base class for all section generators — Strands Agentic Version.

Each section generator is now backed by a Strands Agent.  Subclasses that
deal with financial data (sections 06, 07) can override ``get_tools()``
to equip the agent with arithmetic/verification tools.
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod

from strands import Agent
from strands.models.bedrock import BedrockModel

from lambdas.shared.models import CrosswalkData
from lambdas.shared import s3_utils

logger = logging.getLogger(__name__)

REGION = os.environ.get("AWS_REGION", "us-east-1")

MODELS = {
    "haiku": "anthropic.claude-haiku-4-5-20251001-v1:0",
    "sonnet": "anthropic.claude-sonnet-4-5-20250929-v1:0",
    "opus": "anthropic.claude-opus-4-6-v1",
}


class SectionGenerator(ABC):
    """Abstract base for every appraisal-section Lambda.

    Subclasses implement the abstract methods; the ``execute`` method
    orchestrates the full generate-and-persist workflow.  Each generation
    call is handled by a Strands Agent backed by the appropriate Bedrock
    model and optional tools.
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
    # Agent tools — override in financial sections
    # ------------------------------------------------------------------

    def get_tools(self) -> list:
        """Return Strands tools for this section's agent.

        Override in subclasses that need arithmetic / verification
        tools (e.g. section_06, section_07).  Default: no tools.
        """
        return []

    def get_max_tokens(self) -> int:
        """Return the max output tokens for this section's model.

        Override in subclasses that produce extra-long output.
        """
        return 8192

    def get_temperature(self) -> float:
        """Return the sampling temperature for this section.

        Override in subclasses that need tighter or looser generation.
        """
        return 0.7

    # ------------------------------------------------------------------
    # Template workflow
    # ------------------------------------------------------------------

    def _create_agent(self) -> Agent:
        """Build a Strands Agent for this section's generation task."""
        model_name = self.get_model_name()
        model = BedrockModel(
            model_id=MODELS[model_name],
            region_name=REGION,
            max_tokens=self.get_max_tokens(),
            temperature=self.get_temperature(),
        )

        tools = self.get_tools()
        return Agent(
            name=self.get_section_name(),
            model=model,
            system_prompt=self.get_system_prompt(),
            tools=tools if tools else [],
        )

    def generate_content(self, prompt: str) -> str:
        """Generate section content via a Strands Agent."""
        agent = self._create_agent()
        result = agent(prompt)
        return str(result)

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
