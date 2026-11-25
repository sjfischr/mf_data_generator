import boto3
import pytest

try:
    import fal_client
except ImportError:
    fal_client = None

from strands.models import bedrock as strands_bedrock


@pytest.fixture(autouse=True)
def prevent_live_external_clients(monkeypatch):
    original_boto3_client = boto3.client

    def guarded_boto3_client(service_name, *args, **kwargs):
        if service_name in {"bedrock", "bedrock-runtime"}:
            raise RuntimeError(
                "Live Bedrock calls are forbidden in unit tests; mock the Bedrock client "
                "or Strands Agent instead."
            )
        return original_boto3_client(service_name, *args, **kwargs)

    monkeypatch.setattr(boto3, "client", guarded_boto3_client)

    def guarded_bedrock_model_init(self, *args, **kwargs):
        raise RuntimeError(
            "Live Strands BedrockModel construction is forbidden in unit tests."
        )

    monkeypatch.setattr(
        strands_bedrock.BedrockModel,
        "__init__",
        guarded_bedrock_model_init,
    )

    if fal_client is not None:
        def guarded_fal_run(*args, **kwargs):
            raise RuntimeError(
                "Outbound fal.ai calls are forbidden in unit tests; mock fal_client.run."
            )

        monkeypatch.setattr(fal_client, "run", guarded_fal_run)

