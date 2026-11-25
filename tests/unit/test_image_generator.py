from unittest.mock import MagicMock, patch

from lambdas.image_generator import handler as image_handler


@patch("lambdas.image_generator.handler.s3_utils.write_bytes")
@patch("lambdas.image_generator.handler.requests.get")
@patch("lambdas.image_generator.handler.fal_client.run")
def test_turbo_render_is_deterministic(mock_run, mock_get, mock_write):
    mock_run.return_value = {
        "images": [{"url": "https://example.test/image.jpeg"}],
        "has_nsfw_concepts": [False],
    }
    mock_get.return_value.raise_for_status = MagicMock()
    mock_get.return_value.content = b"fake-jpeg"
    mock_write.return_value = "jobs/job/images/aerial_view.jpg"

    result = image_handler.generate_single_image(
        {
            "filename": "aerial_view.jpg",
            "description": "Aerial view",
            "prompt": "A modern property",
        },
        "job-123",
    )

    assert result["status"] == "success"
    arguments = mock_run.call_args.kwargs["arguments"]
    assert mock_run.call_args.args[0] == "fal-ai/krea-2/turbo"
    assert arguments["output_format"] == "jpeg"
    assert arguments["enable_prompt_expansion"] is False
    assert arguments["image_size"] == "landscape_4_3"
    assert 0 <= arguments["seed"] < 2**31


@patch("lambdas.image_generator.handler.s3_utils.write_bytes")
@patch("lambdas.image_generator.handler.requests.get")
@patch("lambdas.image_generator.handler.fal_client.run")
def test_safety_filter_retries_once(mock_run, mock_get, mock_write):
    mock_run.return_value = {
        "images": [{"url": "https://example.test/image.jpeg"}],
        "has_nsfw_concepts": [True],
    }

    result = image_handler.generate_single_image(
        {
            "filename": "aerial_view.jpg",
            "description": "Aerial view",
            "prompt": "A modern property",
        },
        "job-123",
    )

    assert result["status"] == "failed"
    assert result["reason"] == "safety_filter"
    assert mock_run.call_count == 2

def _fake_batch(**kwargs):
    import re
    count = int(re.search(r"generate exactly (\d+)", kwargs["prompt"]).group(1))
    prefix = re.search(r'Prefix every filename with "(\w+)_"', kwargs["prompt"]).group(1)
    return [{"filename": f"{prefix}_shot_{i}.jpg", "description": "d", "subject": "s"} for i in range(count)]


def test_build_image_prompts_batches_to_thirty(finalized_crosswalk, mocker):
    mocker.patch.object(image_handler, "generate_architectural_concept", return_value={"style": "craftsman"})
    invoke = mocker.patch.object(image_handler.bedrock_client, "invoke_model_json", side_effect=_fake_batch)
    prompts = image_handler.build_image_prompts(finalized_crosswalk)
    assert len(prompts) == 30 and invoke.call_count == 3
    assert len({p["filename"] for p in prompts}) == 30
    assert all("Subject: s" in p["prompt"] for p in prompts)


def test_short_prompt_batch_retries_then_fails(finalized_crosswalk, mocker):
    import pytest

    mocker.patch.object(image_handler, "generate_architectural_concept", return_value={})
    invoke = mocker.patch.object(image_handler.bedrock_client, "invoke_model_json",
                                 return_value=[{"filename": "a.jpg", "subject": "s"}])
    with pytest.raises(RuntimeError, match="returned 1 prompts; expected 10"):
        image_handler._generate_batch(finalized_crosswalk, {}, image_handler.SHOT_BATCHES[0])
    assert invoke.call_count == 2
