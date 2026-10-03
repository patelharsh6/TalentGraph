"""Error hierarchy. API handlers map these to RFC 7807 problem responses (plan §8.1)."""


class TalentGraphError(Exception):
    code: str = "internal_error"
    http_status: int = 500
    retryable: bool = False
    title: str = "Internal error"

    def __init__(self, detail: str = "", *, retryable: bool | None = None) -> None:
        super().__init__(detail or self.title)
        self.detail = detail or self.title
        if retryable is not None:
            self.retryable = retryable


class UnsupportedFileType(TalentGraphError):
    code = "unsupported_file_type"
    http_status = 415
    title = "Unsupported file type"


class FileTooLarge(TalentGraphError):
    code = "file_too_large"
    http_status = 413
    title = "File too large"


class UnsupportedContent(TalentGraphError):
    code = "unsupported_content"
    http_status = 422
    title = "Unsupported content"


class NotFound(TalentGraphError):
    code = "not_found"
    http_status = 404
    title = "Resource not found"


class LLMError(TalentGraphError):
    code = "llm_error"
    http_status = 502
    title = "LLM call failed"
    retryable = True


class LLMQuotaExceeded(LLMError):
    code = "llm_quota_exceeded"
    title = "LLM quota exceeded"
    retryable = False


class AgentTimeout(TalentGraphError):
    code = "agent_timeout"
    http_status = 504
    title = "Agent timed out"
    retryable = True
