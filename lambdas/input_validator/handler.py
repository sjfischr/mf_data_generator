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
from lambdas.shared import s3_utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

STEP_FUNCTION_ARN = os.environ.get("STEP_FUNCTION_ARN", "")

_sfn_client = None

REQUIRED_FIELDS = [
    "address",
    "city",
    "state",
    "units",
    "year_built",
    "property_type",
]
ALLOWED_PROPERTY_TYPES = {"garden-style", "mid-rise", "high-rise"}


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


def _validate_input(raw_body: dict) -> tuple[dict | None, list[dict]]:
    errors: list[dict] = []

    for field in REQUIRED_FIELDS:
        if field not in raw_body:
            errors.append({"field": field, "message": "Field required", "type": "missing"})

    if errors:
        return None, errors

    try:
        units = int(raw_body["units"])
        if units <= 0:
            raise ValueError("must be greater than 0")
    except Exception:
        errors.append({"field": "units", "message": "units must be a positive integer", "type": "value_error"})
        units = raw_body.get("units")

    try:
        year_built = int(raw_body["year_built"])
        if year_built < 1800 or year_built > 2100:
            raise ValueError("out of range")
    except Exception:
        errors.append({"field": "year_built", "message": "year_built must be an integer between 1800 and 2100", "type": "value_error"})
        year_built = raw_body.get("year_built")

    property_type = str(raw_body.get("property_type", "")).strip()
    if property_type not in ALLOWED_PROPERTY_TYPES:
        errors.append({
            "field": "property_type",
            "message": "property_type must be one of: garden-style, mid-rise, high-rise",
            "type": "value_error",
        })

    validated = {
        "property_name": str(raw_body.get("property_name", "")).strip(),
        "address": str(raw_body.get("address", "")).strip(),
        "city": str(raw_body.get("city", "")).strip(),
        "state": str(raw_body.get("state", "")).strip(),
        "units": units,
        "year_built": year_built,
        "property_type": property_type,
    }

    for field in ["address", "city", "state"]:
        if not validated[field]:
            errors.append({"field": field, "message": f"{field} cannot be empty", "type": "value_error"})

    return (validated if not errors else None), errors


def handler(event, context):
    """AWS Lambda entry point.

    Expects an API Gateway proxy event whose *body* is a JSON string with
    the fields defined by ``UserInput``.
    """
    logger.info("Received event: %s", json.dumps(event, default=str))

    # ------------------------------------------------------------------
    # 0. Step Functions passthrough mode
    # ------------------------------------------------------------------
    if isinstance(event, dict) and "job_id" in event and "body" not in event:
        return {
            "job_id": event["job_id"],
            "status": "validated",
        }

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
    # 2. Validate request fields
    # ------------------------------------------------------------------
    user_input, validation_errors = _validate_input(raw_body)
    if validation_errors:
        logger.warning("Validation failed: %s", validation_errors)
        return _api_response(400, {
            "error": "Validation failed.",
            "details": validation_errors,
        })

    # ------------------------------------------------------------------
    # 3. Create job
    # ------------------------------------------------------------------
    job_id = str(uuid.uuid4())
    logger.info("Created job_id=%s for %s, %s %s",
                job_id, user_input["address"], user_input["city"], user_input["state"])

    # Create the S3 folder structure
    s3_utils.create_job_structure(job_id)

    # Persist the validated input
    input_dict = dict(user_input)
    input_dict["job_id"] = job_id
    s3_utils.write_json(job_id, "input.json", input_dict)

    # ------------------------------------------------------------------
    # 4. Start Step Functions execution
    # ------------------------------------------------------------------
    sfn = _get_sfn_client()
    execution_input = json.dumps({"job_id": job_id})

    try:
        execution_name = f"appraisal-{job_id}"
        sfn_response = sfn.start_execution(
            stateMachineArn=STEP_FUNCTION_ARN,
            name=execution_name,
            input=execution_input,
        )
        execution_arn = sfn_response["executionArn"]
        logger.info("Started execution %s", execution_arn)

        # Persist execution identifiers so status polling can resolve directly.
        input_dict["execution_name"] = execution_name
        input_dict["execution_arn"] = execution_arn
        s3_utils.write_json(job_id, "input.json", input_dict)
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
