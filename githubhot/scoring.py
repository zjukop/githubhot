from __future__ import annotations

from datetime import datetime, timezone
from math import log10

from githubhot.models import Repository


def _parse_github_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def score_repository(repo: Repository, now: datetime | None = None) -> Repository:
    """Rank discoverability signals without claiming product quality.

    GitHub's public search API does not expose historical star counts. The score
    therefore uses repository age, engagement and freshness as candidate signals.
    Daily snapshots can later provide true star-growth measurements.
    """
    now = now or datetime.now(timezone.utc)
    created = _parse_github_time(repo.created_at)
    pushed = _parse_github_time(repo.pushed_at)
    age_days = max((now - created).total_seconds() / 86400, 1)
    push_age_days = max((now - pushed).total_seconds() / 86400, 0)

    star_velocity = repo.stars / age_days
    engagement = (repo.forks + repo.open_issues * 0.35) / max(repo.stars, 1)
    freshness = max(0.0, 1.0 - push_age_days / 30)

    score = (
        min(log10(repo.stars + 1) / 5, 1) * 25
        + min(log10(star_velocity + 1) / 3, 1) * 35
        + min(engagement * 4, 1) * 15
        + freshness * 15
        + (5 if repo.license and repo.license != "NOASSERTION" else 0)
        + (5 if repo.description else 0)
    )

    reasons = [
        f"{repo.stars:,} stars over {age_days:.0f} days",
        f"estimated {star_velocity:.1f} stars/day since creation",
        f"last push {push_age_days:.1f} days ago",
    ]
    if repo.license and repo.license != "NOASSERTION":
        reasons.append(f"detectable {repo.license} license")
    if repo.topics:
        reasons.append(f"topics: {', '.join(repo.topics[:5])}")

    repo.score = round(score, 2)
    repo.score_reasons = reasons
    return repo

