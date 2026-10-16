"""Fixed-window rate limiting on top of the key-value store."""

import time
from dataclasses import dataclass

from app.core.exceptions import RateLimitedError
from app.core.store import Store


@dataclass(frozen=True, slots=True)
class RateLimit:
    """At most `limit` hits per `window_seconds` for one key."""

    name: str
    limit: int
    window_seconds: int


# Per-IP limits are generous because a whole classroom may share one NAT address;
# Turnstile and the per-account limits do the fine-grained work.
LOGIN_PER_IP = RateLimit("login_ip", 60, 60)
LOGIN_PER_EMAIL = RateLimit("login_email", 5, 60)
REGISTER_PER_IP = RateLimit("register_ip", 40, 3600)
EMAIL_ACTION_PER_EMAIL = RateLimit("email_action", 3, 3600)
EMAIL_ACTION_PER_IP = RateLimit("email_action_ip", 40, 3600)
REFRESH_PER_IP = RateLimit("refresh_ip", 240, 60)
API_PER_USER = RateLimit("api_user", 120, 60)
LLM_PER_USER = RateLimit("llm_user", 10, 60)
ACCESS_REQUEST_PER_USER = RateLimit("access_request", 3, 86400)


class RateLimiter:
    """Count hits per key and reject those over the limit."""

    def __init__(self, store: Store) -> None:
        self._store = store

    async def hit(self, rule: RateLimit, key: str) -> None:
        """Record a hit; raise RateLimitedError when the window is full."""
        now = int(time.time())
        window = now // rule.window_seconds
        count = await self._store.incr(f"rl:{rule.name}:{key}:{window}", rule.window_seconds)
        if count > rule.limit:
            retry_after = (window + 1) * rule.window_seconds - now
            raise RateLimitedError(retry_after=max(retry_after, 1))
