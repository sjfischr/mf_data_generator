from lambdas.lender_narrative_generator import handler as narrative


def test_narrative_has_all_sections_in_order(finalized_crosswalk, mocker):
    mocker.patch.object(narrative.bedrock_client, "invoke_model", side_effect=lambda **kw: _sections_for(kw["prompt"]))
    markdown, warnings = narrative.build_narrative(finalized_crosswalk)
    positions = [markdown.index(f"## {h}") for h in narrative.HEADINGS]
    assert positions == sorted(positions)
    assert f"${finalized_crosswalk.financing.loan_amount:,}" in markdown
    assert warnings == []


def _sections_for(prompt: str) -> str:
    listed = prompt.split("Write these Transaction Approval Memo sections:")[1].split("\n")[0]
    numbers = [h.split(".")[0].strip() for h in listed.split(", ") if h.strip()[:1].isdigit()]
    return "\n".join(f"@@SECTION {n}@@\nAnalysis for section {n}." for n in numbers)


def test_unsupported_figure_triggers_one_regeneration(finalized_crosswalk, mocker):
    calls = []

    def respond(**kw):
        calls.append(kw["prompt"])
        text = _sections_for(kw["prompt"])
        return text + " The loan is $1,234,567." if len(calls) == 1 else text

    mocker.patch.object(narrative.bedrock_client, "invoke_model", side_effect=respond)
    sections, warnings = narrative.generate_group([2], "Summarize.", "{}", {"$": [], "%": [], "x": []})
    assert len(calls) == 2
    assert "previous draft cited figures" in calls[1]
    assert warnings == [] and "Analysis for section 2." in sections[2]


def test_number_guard_accepts_rounded_figures_and_rejects_unknown():
    allowed = narrative.allowed_numbers("$13,899,000 94.20% 1.25x")
    assert narrative.unsupported_figures("about 94% occupied, $13.9 million loan, 1.25x DSCR", allowed) == []
    assert narrative.unsupported_figures("a $2,000,000 loan at 1.40x", allowed) == ["$2,000,000", "1.40x"]
