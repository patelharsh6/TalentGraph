"""Step 5.3: slowapi per-IP rate limiting (plan §8.1)."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from talentgraph.config import get_settings


def create_limiter() -> Limiter:
    """Create a configured SlowAPI Limiter instance."""
    settings = get_settings()
    return Limiter(
        key_func=get_remote_address,
        default_limits=[f"{settings.rate_limit_per_min}/minute"],
        headers_enabled=True,
    )


limiter = create_limiter()
