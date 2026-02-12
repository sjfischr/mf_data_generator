"""Status Checker Lambda — returns Step Functions execution status for a job."""

import json
import logging
import os

import boto3

logger = logging.getLogger(__name__)

SFN_ARN = os.environ.get("STEP_FUNCTION_ARN", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")

STEP_PROGRESS = {
    "InputValidator": 5,
    "CrosswalkGenerator": 15,
    "GenerateAllSections": 60,
    "ImageGenerator": 75,
    "QCValidator": 85,
    "Assembler": 95,
}


def handler(event, context):
    job_id = event.get("pathParameters", {}).get("job_id", "")

    if not job_id:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Missing job_id"}),
        }

    sfn = boto3.client("stepfunctions", region_name=REGION)

    # List executions filtered by name (job_id is used as execution name)
    try:
        response = sfn.list_executions(
            stateMachineArn=SFN_ARN,
            statusFilter="RUNNING",
            maxResults=100,
        )

        execution = None
        for ex in response.get("executions", []):
            if ex["name"] == job_id:
                execution = ex
                break

        if not execution:
            # Check completed executions
            for status_filter in ["SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"]:
                response = sfn.list_executions(
                    stateMachineArn=SFN_ARN,
                    statusFilter=status_filter,
                    maxResults=50,
                )
                for ex in response.get("executions", []):
                    if ex["name"] == job_id:
                        execution = ex
                        break
                if execution:
                    break

        if not execution:
            return {
                "statusCode": 404,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Job not found", "job_id": job_id}),
            }

        sfn_status = execution["status"]

        # Map Step Functions status to our status
        status_map = {
            "RUNNING": "running",
            "SUCCEEDED": "succeeded",
            "FAILED": "failed",
            "TIMED_OUT": "failed",
            "ABORTED": "failed",
        }

        # Try to determine current step and progress
        progress = 0
        current_step = None

        if sfn_status == "RUNNING":
            describe = sfn.describe_execution(executionArn=execution["executionArn"])
            # Get execution history to find current state
            history = sfn.get_execution_history(
                executionArn=execution["executionArn"],
                reverseOrder=True,
                maxResults=5,
            )
            for evt in history.get("events", []):
                if "stateEnteredEventDetails" in evt:
                    current_step = evt["stateEnteredEventDetails"]["name"]
                    progress = STEP_PROGRESS.get(current_step, 50)
                    break
        elif sfn_status == "SUCCEEDED":
            progress = 100
            current_step = "Complete"
        else:
            progress = 0
            current_step = "Failed"

        result = {
            "job_id": job_id,
            "status": status_map.get(sfn_status, "unknown"),
            "progress": progress,
            "current_step": current_step,
        }

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps(result),
        }

    except Exception as e:
        logger.error("Error checking status for job %s: %s", job_id, e)
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }
