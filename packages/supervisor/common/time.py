from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def freshness_seconds(latest: datetime | None, now: datetime | None = None) -> int | None:
    if latest is None:
        return None
    anchor = now or utc_now()
    return max(0, int((anchor - latest).total_seconds()))