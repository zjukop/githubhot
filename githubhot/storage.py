from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from githubhot.models import Repository


def write_candidates(path: Path, repos: list[Repository], query: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": date.today().isoformat(),
        "query": query,
        "repositories": [repo.to_dict() for repo in repos],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_candidates(path: Path) -> list[Repository]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [Repository(**item) for item in payload["repositories"]]


def read_candidate_payload(path: Path) -> tuple[str, list[Repository]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("query", "unknown"), [Repository(**item) for item in payload["repositories"]]


def write_snapshot(root: Path, repos: list[Repository], snapshot_date: date | None = None) -> Path:
    snapshot_date = snapshot_date or date.today()
    path = root / f"{snapshot_date.isoformat()}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {repo.full_name: repo.to_dict() for repo in repos}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
