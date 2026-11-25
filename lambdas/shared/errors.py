"""Shared error types for transient pipeline stages."""

from __future__ import annotations


class TransientError(RuntimeError):
    """An operation failed because of a recoverable external-service error."""


def wrap_transient(exc: Exception) -> Exception:
    code = ""
    if hasattr(exc, "response"):
        code = str(exc.response.get("Error", {}).get("Code", ""))
    text = str(exc)
    if (
        code in {
            "ThrottlingException",
            "ServiceUnavailableException",
            "ModelNotReadyException",
            "InternalServerException",
            "TooManyRequestsException",
        }
        or "429" in text
        or " 5" in text
        or "throttl" in text.lower()
    ):
        return TransientError(text)
    return exc
