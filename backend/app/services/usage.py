"""Per-client daily analysis allowance (free tier).

In-memory on purpose: no database is needed for the first launch. Counts
reset when the server restarts or redeploys, and each server instance keeps
its own counts, which is acceptable while running a single instance. Move
this to Postgres/Redis together with user accounts.
"""

import threading
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Request


@dataclass(frozen=True)
class UsageStatus:
    limit: int
    used: int

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)

    @property
    def unlimited(self) -> bool:
        return self.limit <= 0


class DailyUsageLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._day = ""
        self._counts: dict[str, int] = {}

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).date().isoformat()

    def _roll_day(self) -> None:
        today = self._today()
        if today != self._day:
            self._day = today
            self._counts.clear()

    def status(self, client_id: str, limit: int) -> UsageStatus:
        with self._lock:
            self._roll_day()
            return UsageStatus(limit=limit, used=self._counts.get(client_id, 0))

    def try_consume(self, client_id: str, limit: int) -> UsageStatus | None:
        """Reserve one analysis. Returns None when the allowance is used up."""
        with self._lock:
            self._roll_day()
            used = self._counts.get(client_id, 0)
            if limit > 0 and used >= limit:
                return None
            self._counts[client_id] = used + 1
            return UsageStatus(limit=limit, used=used + 1)

    def refund(self, client_id: str) -> None:
        """Give an analysis back when it failed on our side."""
        with self._lock:
            self._roll_day()
            used = self._counts.get(client_id, 0)
            if used > 0:
                self._counts[client_id] = used - 1

    def reset(self) -> None:
        with self._lock:
            self._counts.clear()


limiter = DailyUsageLimiter()


def client_id_from_request(request: Request, trusted_proxy_hops: int = 1) -> str:
    """Best-effort client IP.

    Railway and Render put the real client IP at the end of X-Forwarded-For.
    Entries further left can be set by the client, so they are not trusted.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    hops = [part.strip() for part in forwarded.split(",") if part.strip()]
    if hops and trusted_proxy_hops > 0:
        index = max(0, len(hops) - trusted_proxy_hops)
        return hops[index]
    return request.client.host if request.client else "unknown"
