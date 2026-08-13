from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Repository:
    full_name: str
    html_url: str
    description: str
    stars: int
    forks: int
    open_issues: int
    watchers: int
    language: str | None
    license: str | None
    topics: list[str]
    created_at: str
    updated_at: str
    pushed_at: str
    archived: bool = False
    fork: bool = False
    score: float = 0.0
    score_reasons: list[str] = field(default_factory=list)

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> "Repository":
        license_info = payload.get("license") or {}
        return cls(
            full_name=payload["full_name"],
            html_url=payload["html_url"],
            description=(payload.get("description") or "").strip(),
            stars=int(payload.get("stargazers_count", 0)),
            forks=int(payload.get("forks_count", 0)),
            open_issues=int(payload.get("open_issues_count", 0)),
            watchers=int(payload.get("subscribers_count", payload.get("watchers_count", 0))),
            language=payload.get("language"),
            license=license_info.get("spdx_id"),
            topics=list(payload.get("topics") or []),
            created_at=payload.get("created_at", ""),
            updated_at=payload.get("updated_at", ""),
            pushed_at=payload.get("pushed_at", ""),
            archived=bool(payload.get("archived", False)),
            fork=bool(payload.get("fork", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

