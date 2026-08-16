from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path


def published_dates(daily_dir: Path) -> set[date]:
    dates: set[date] = set()
    for path in daily_dir.glob("*/*/*.md"):
        try:
            dates.add(date.fromisoformat(path.stem))
        except ValueError:
            continue
    return dates


def missing_publish_dates(daily_dir: Path, target_date: date, limit: int = 7) -> list[date]:
    if limit < 1:
        raise ValueError("limit must be positive")
    published = published_dates(daily_dir)
    if not published:
        return [target_date]
    start = min(published)
    if start > target_date:
        return [target_date]
    missing: list[date] = []
    current = start
    while current <= target_date and len(missing) < limit:
        if current not in published:
            missing.append(current)
        current += timedelta(days=1)
    return missing
