"""Lambda: Input Validator.

Receives an API Gateway event, validates user input with Pydantic,
creates the S3 job structure, and starts the Step Functions state machine.
"""

from __future__ import annotations

import json
import logging
import os
import uuid

import boto3
from pydantic import ValidationError

from lambdas.shared.models import UserInput
from lambdas.shared import s3_utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

STEP_FUNCTION_ARN = os.environ.get("STEP_FUNCTION_ARN", "")

_sfn_client = None


def _get_sfn_client():
    global _sfn_client
    if _sfn_client is None:
        _sfn_client = boto3.client("stepfunctions")
    return _sfn_client


def _api_response(status_code: int, body: dict) -> dict:
    """Build a properly-formatted API Gateway proxy response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        },
        "body": json.dumps(body),
    }


def handler(event, context):
    """AWS Lambda entry point.

    Expects an API Gateway proxy event whose *body* is a JSON string with
    the fields defined by ``UserInput``.
    """
    logger.info("Received event: %s", json.dumps(event, default=str))

    # ------------------------------------------------------------------
    # 1. Parse body
    # ------------------------------------------------------------------
    try:
        if isinstance(event.get("body"), str):
            raw_body = json.loads(event["body"])
        elif isinstance(event.get("body"), dict):
            raw_body = event["body"]
        else:
            # Direct invocation (e.g. from Step Functions or test console)
            raw_body = event
    except (json.JSONDecodeError, TypeError) as exc:
        logger.error("Bad request body: %s", exc)
        return _api_response(400, {"error": "Invalid JSON in request body."})

    # ------------------------------------------------------------------
    # 2. Validate with Pydantic
    # ------------------------------------------------------------------
    try:
        user_input = UserInput.model_validate(raw_body)
    except ValidationError as exc:
        logger.warning("Validation failed: %s", exc)
        errors = exc.errors()
        return _api_response(400, {
            "error": "Validation failed.",
            "details": [
                {
                    "field": ".".join(str(loc) for loc in e["loc"]),
                    "message": e["msg"],
                    "type": e["type"],
                }
                for e in errors
            ],
        })

    # ------------------------------------------------------------------
    # 3. Create job
    # ------------------------------------------------------------------
    job_id = str(uuid.uuid4())
    logger.info("Created job_id=%s for %s, %s %s",
                job_id, user_input.address, user_input.city, user_input.state)

    # Create the S3 folder structure
    s3_utils.create_job_structure(job_id)

    # Persist the validated input
    input_dict = user_input.model_dump()
    input_dict["job_id"] = job_id
    s3_utils.write_json(job_id, "input.json", input_dict)

    # ------------------------------------------------------------------
    # 4. Start Step Functions execution
    # ------------------------------------------------------------------
    sfn = _get_sfn_client()
    execution_input = json.dumps({"job_id": job_id})

    try:
        sfn_response = sfn.start_execution(
            stateMachineArn=STEP_FUNCTION_ARN,
            name=f"appraisal-{job_id}",
            input=execution_input,
        )
        execution_arn = sfn_response["executionArn"]
        logger.info("Started execution %s", execution_arn)
    except Exception:
        logger.exception("Failed to start Step Functions execution")
        # The job data is already persisted -- we can still return the job_id
        # and let the caller retry or investigate.
        return _api_response(500, {
            "error": "Failed to start processing pipeline.",
            "job_id": job_id,
        })

    # ------------------------------------------------------------------
    # 5. Return success
    # ------------------------------------------------------------------
    return _api_response(200, {
        "job_id": job_id,
        "status": "processing",
        "execution_arn": execution_arn,
    })
