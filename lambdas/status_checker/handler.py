"""Status Checker Lambda — returns Step Functions execution status for a job."""

import json
import logging
import os

import boto3
from lambdas.shared import s3_utils

logger = logging.getLogger(__name__)

SFN_ARN = os.environ.get("STEP_FUNCTION_ARN", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")

STEP_PROGRESS = {
    "ValidateInput": 5,
    "GenerateCrosswalk": 15,
    "GenerateAllSections": 60,
    "GenerateImages": 75,
    "RunQCValidation": 85,
    "QCPassOrFail": 90,
    "AssembleReport": 95,
    "NotifySuccess": 99,
    "PipelineSucceeded": 100,
}

TERMINAL_STATUSES = ["SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"]


def _status_response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body),
    }


def _get_known_execution_arn(job_id: str) -> str | None:
    try:
        input_data = s3_utils.read_json(job_id, "input.json")
        execution_arn = input_data.get("execution_arn")
        if isinstance(execution_arn, str) and execution_arn.strip():
            return execution_arn
    except Exception:
        # Not fatal: fallback to listing executions.
        pass
    return None


def _find_execution_by_name(sfn, job_id: str) -> dict | None:
    candidate_names = {job_id, f"appraisal-{job_id}"}

    for status_filter in ["RUNNING", *TERMINAL_STATUSES]:
        next_token = None
        while True:
            params = {
                "stateMachineArn": SFN_ARN,
                "statusFilter": status_filter,
                "maxResults": 100,
            }
            if next_token:
                params["nextToken"] = next_token

            response = sfn.list_executions(**params)
            for execution in response.get("executions", []):
                ex_name = execution.get("name", "")
                if ex_name in candidate_names or ex_name.endswith(job_id):
                    return execution

            next_token = response.get("nextToken")
            if not next_token:
                break

    return None


def _extract_progress(sfn, execution_arn: str, sfn_status: str) -> tuple[int, str | None, str | None]:
    if sfn_status == "SUCCEEDED":
        return 100, "PipelineSucceeded", None

    history = sfn.get_execution_history(
        executionArn=execution_arn,
        reverseOrder=True,
        maxResults=50,
    )

    current_step = None
    error_message = None

    for event in history.get("events", []):
        details = event.get("stateEnteredEventDetails")
        if details and details.get("name"):
            current_step = details["name"]
            break

    if sfn_status in {"FAILED", "TIMED_OUT", "ABORTED"}:
        for event in history.get("events", []):
            failed = event.get("executionFailedEventDetails") or event.get("taskFailedEventDetails")
            if failed:
                cause = failed.get("cause") or ""
                error = failed.get("error") or ""
                error_message = f"{error}: {cause}".strip(": ") or "Pipeline execution failed"
                break

    if sfn_status == "RUNNING":
        progress = STEP_PROGRESS.get(current_step or "", 5)
    else:
        progress = STEP_PROGRESS.get(current_step or "", 0)

    return progress, current_step, error_message


def handler(event, context):
    job_id = event.get("pathParameters", {}).get("job_id", "")

    if not job_id:
        return _status_response(400, {"error": "Missing job_id"})

    sfn = boto3.client("stepfunctions", region_name=REGION)

    try:
        execution_arn = _get_known_execution_arn(job_id)
        execution_details = None

        if execution_arn:
            execution_details = sfn.describe_execution(executionArn=execution_arn)
            execution = {
                "name": execution_details.get("name", ""),
                "executionArn": execution_arn,
                "status": execution_details.get("status", ""),
                "startDate": execution_details.get("startDate"),
                "stopDate": execution_details.get("stopDate"),
            }
        else:
            execution = _find_execution_by_name(sfn, job_id)
            if execution:
                execution_arn = execution["executionArn"]
                execution_details = sfn.describe_execution(executionArn=execution_arn)

        if not execution:
            return _status_response(404, {"error": "Job not found", "job_id": job_id})

        sfn_status = execution.get("status", "")

        # Map Step Functions status to our status
        status_map = {
            "RUNNING": "running",
            "SUCCEEDED": "succeeded",
            "FAILED": "failed",
            "TIMED_OUT": "failed",
            "ABORTED": "failed",
        }

        progress, current_step, error_message = _extract_progress(sfn, execution_arn, sfn_status)

        result = {
            "job_id": job_id,
            "status": status_map.get(sfn_status, "unknown"),
            "progress": progress,
            "current_step": current_step,
            "execution_name": execution.get("name"),
            "execution_arn": execution_arn,
        }

        if execution.get("startDate"):
            result["started_at"] = execution["startDate"].isoformat()
        if execution.get("stopDate"):
            result["completed_at"] = execution["stopDate"].isoformat()
        if error_message:
            result["error"] = error_message

        return _status_response(200, result)

    except Exception as e:
        logger.error("Error checking status for job %s: %s", job_id, e)
        return _status_response(500, {"error": str(e), "job_id": job_id})
