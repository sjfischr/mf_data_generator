"""S3 utilities for reading/writing job data."""

from __future__ import annotations

import json
import logging
import os

import boto3

logger = logging.getLogger(__name__)

BUCKET = os.environ.get("S3_BUCKET", "synthetic-appraisals")

_s3 = None


def get_s3_client():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3")
    return _s3


def job_key(job_id: str, path: str) -> str:
    """Build an S3 key for a job artifact."""
    return f"jobs/{job_id}/{path}"


def read_json(job_id: str, filename: str) -> dict:
    """Read a JSON file from the job's S3 folder."""
    key = job_key(job_id, filename)
    logger.info("Reading s3://%s/%s", BUCKET, key)
    s3 = get_s3_client()
    obj = s3.get_object(Bucket=BUCKET, Key=key)
    return json.loads(obj["Body"].read().decode("utf-8"))


def write_json(job_id: str, filename: str, data: dict) -> str:
    """Write a JSON file to the job's S3 folder. Returns the S3 key."""
    key = job_key(job_id, filename)
    logger.info("Writing s3://%s/%s", BUCKET, key)
    s3 = get_s3_client()
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=json.dumps(data, indent=2),
        ContentType="application/json",
    )
    return key


def read_text(job_id: str, filename: str) -> str:
    """Read a text/markdown file from the job's S3 folder."""
    key = job_key(job_id, filename)
    s3 = get_s3_client()
    obj = s3.get_object(Bucket=BUCKET, Key=key)
    return obj["Body"].read().decode("utf-8")


def write_text(job_id: str, filename: str, content: str) -> str:
    """Write a text/markdown file to the job's S3 folder. Returns the S3 key."""
    key = job_key(job_id, filename)
    logger.info("Writing s3://%s/%s", BUCKET, key)
    s3 = get_s3_client()
    content_type = (
        "text/markdown" if filename.endswith(".md") else "text/plain"
    )
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=content.encode("utf-8"),
        ContentType=content_type,
    )
    return key


def write_bytes(job_id: str, filename: str, data: bytes, content_type: str) -> str:
    """Write binary data to the job's S3 folder. Returns the S3 key."""
    key = job_key(job_id, filename)
    logger.info("Writing s3://%s/%s", BUCKET, key)
    s3 = get_s3_client()
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return key


def list_files(job_id: str, prefix: str = "") -> list[str]:
    """List all files in a job's S3 folder (optionally under a sub-prefix)."""
    full_prefix = job_key(job_id, prefix)
    s3 = get_s3_client()
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix=full_prefix)
    if "Contents" not in response:
        return []
    return [obj["Key"] for obj in response["Contents"]]


def generate_presigned_url(job_id: str, filename: str, expires_in: int = 604800) -> str:
    """Generate a presigned download URL (default 7 days)."""
    key = job_key(job_id, filename)
    s3 = get_s3_client()
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": key},
        ExpiresIn=expires_in,
    )


def create_job_structure(job_id: str) -> None:
    """Create the initial folder structure for a new job."""
    s3 = get_s3_client()
    for folder in ["sections/", "images/", "outputs/"]:
        key = job_key(job_id, folder)
        s3.put_object(Bucket=BUCKET, Key=key, Body=b"")
