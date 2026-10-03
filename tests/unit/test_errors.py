from talentgraph.core.errors import LLMError, LLMQuotaExceeded, UnsupportedFileType


def test_error_defaults() -> None:
    err = UnsupportedFileType("Detected image/png")
    assert (err.code, err.http_status, err.retryable) == ("unsupported_file_type", 415, False)
    assert err.detail == "Detected image/png"


def test_quota_errors_are_not_retryable() -> None:
    assert LLMError().retryable is True
    assert LLMQuotaExceeded().retryable is False
