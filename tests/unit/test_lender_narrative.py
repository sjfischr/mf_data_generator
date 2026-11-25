import pytest

from lambdas.shared.models import CrosswalkData
from lambdas.lender_narrative_generator.handler import (
    HEADINGS,
    build_narrative,
)


@pytest.fixture
def crosswalk():
    from tests.unit.test_models import sample_crosswalk_dict as fixture
    return CrosswalkData.model_validate(fixture.__pytest_wrapped__.obj())


def test_narrative_contains_all_tam_sections(crosswalk, monkeypatch):
    def fake_invoke_model(*args, **kwargs):
        prompt = kwargs.get("prompt", "")
        if "Executive Summary" in prompt:
            return "The synthetic recommendation is to proceed."
        return "The synthetic underwriter analysis supports the transaction."

    monkeypatch.setattr(
        "lambdas.lender_narrative_generator.handler.bedrock_client.invoke_model",
        fake_invoke_model,
    )
    narrative, warnings = build_narrative(crosswalk)
    for heading in HEADINGS:
        assert f"## {heading}" in narrative
    assert crosswalk.financing is not None
