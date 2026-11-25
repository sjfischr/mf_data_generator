"""Shared error types for transient pipeline stages."""

from __future__ import annotations

TRANSIENT_CODES = {
    "ThrottlingException",
    "ServiceUnavailableException",
    "ModelNotReadyException",
    "InternalServerException",
    "TooManyRequestsException",
    "ModelTimeoutException",
}


class TransientError(RuntimeError):
    """An operation failed because of a recoverable external-service error."""


def is_transient(exc: Exception) -> bool:
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        code = str(response.get("Error", {}).get("Code", ""))
        if code in TRANSIENT_CODES:
            return True
        status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status == 429 or (isinstance(status, int) and status >= 500):
            return True
    status = getattr(exc, "status_code", None) or getattr(response, "status_code", None)
    if status == 429 or (isinstance(status, int) and 500 <= status < 600):
        return True
    return "throttl" in str(exc).lower()


def wrap_transient(exc: Exception) -> Exception:
    """Return a TransientError for recoverable failures, otherwise the original exception."""
    return TransientError(str(exc)) if is_transient(exc) else exc
