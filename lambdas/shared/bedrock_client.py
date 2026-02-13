"""AWS Bedrock client utilities for invoking Claude models."""

from __future__ import annotations

import json
import logging
import os

import boto3

logger = logging.getLogger(__name__)

MODELS = {
    "haiku": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    "sonnet": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "opus": "us.anthropic.claude-opus-4-6-v1",
}

REGION = os.environ.get("AWS_REGION", "us-east-1")

_client = None


def get_bedrock_client():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-runtime", region_name=REGION)
    return _client


def invoke_model(
    prompt: str,
    model: str = "haiku",
    system_prompt: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> str:
    """Invoke a Bedrock Claude model and return the text response.

    Args:
        prompt: The user message to send.
        model: One of "haiku", "sonnet", "opus".
        system_prompt: Optional system message.
        max_tokens: Maximum response tokens.
        temperature: Sampling temperature.

    Returns:
        The model's text response.
    """
    client = get_bedrock_client()
    model_id = MODELS.get(model, model)

    messages = [{"role": "user", "content": prompt}]

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": messages,
        "temperature": temperature,
    }
    if system_prompt:
        body["system"] = system_prompt

    logger.info("Invoking model %s", model_id)

    response = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )

    result = json.loads(response["body"].read())
    return result["content"][0]["text"]


def invoke_model_json(
    prompt: str,
    model: str = "haiku",
    system_prompt: str | None = None,
    max_tokens: int = 8192,
) -> dict:
    """Invoke a model and parse the response as JSON.

    Instructs the model to return valid JSON and extracts it from
    the response, handling markdown code fences if present.
    """
    json_instruction = (
        "\n\nReturn your response as valid JSON only. "
        "Do not include any text outside the JSON object."
    )
    full_prompt = prompt + json_instruction

    text = invoke_model(
        full_prompt,
        model=model,
        system_prompt=system_prompt,
        max_tokens=max_tokens,
        temperature=0.3,
    )

    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (fences)
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    return json.loads(text)
