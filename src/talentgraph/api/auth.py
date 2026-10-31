"""Step 5.2: single X-API-Key check against API_KEY (a blank key disables auth)."""

from fastapi import Header, Request

from talentgraph.config import get_settings
from talentgraph.core.errors import Unauthorized


async def require_api_key(
    request: Request,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> None:
    """Validate X-API-Key header against configured API_KEY on write endpoints.

    If API_KEY is unset or blank in settings, auth is disabled for local dev.
    """
    settings = get_settings()
    configured_key = settings.api_key.get_secret_value() if settings.api_key else None
    if not configured_key:
        return

    if not x_api_key or x_api_key != configured_key:
        raise Unauthorized("Missing or invalid X-API-Key header.")
