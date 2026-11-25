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
