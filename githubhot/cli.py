from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from githubhot.github import GitHubClient, GitHubError
from githubhot.models import Repository
from githubhot.reporting import update_readme_index, write_draft
from githubhot.scoring import score_repository
from githubhot.storage import read_candidates, write_candidates, write_snapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="githubhot", description="Discover and curate fast-growing GitHub repositories.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Fetch and rank repository candidates")
    scan.add_argument("--days", type=int, default=30, help="Only include repositories created in the last N days")
    scan.add_argument("--min-stars", type=int, default=50)
    scan.add_argument("--language")
    scan.add_argument("--topic", action="append", default=[])
    scan.add_argument("--limit", type=int, default=30)
    scan.add_argument("--output", type=Path, default=Path("data/candidates.json"))
    scan.add_argument("--snapshot-dir", type=Path, default=Path("data/snapshots"))

    draft = subparsers.add_parser("draft", help="Create a human-review article draft")
    draft.add_argument("repo", help="Repository full name from the candidate list")
    draft.add_argument("--input", type=Path, default=Path("data/candidates.json"))
    draft.add_argument("--daily-dir", type=Path, default=Path("daily"))
    draft.add_argument("--date", type=date.fromisoformat, default=date.today())

    index = subparsers.add_parser("index", help="Regenerate README daily article index")
    index.add_argument("--readme", type=Path, default=Path("README.md"))
    index.add_argument("--daily-dir", type=Path, default=Path("daily"))
    return parser


def _scan(args: argparse.Namespace) -> int:
    if args.days < 1 or args.min_stars < 0 or args.limit < 1:
        raise ValueError("days and limit must be positive; min-stars cannot be negative")
    created_after = date.today() - timedelta(days=args.days)
    parts = [f"created:>={created_after.isoformat()}", f"stars:>={args.min_stars}", "fork:false", "archived:false"]
    if args.language:
        parts.append(f"language:{args.language}")
    parts.extend(f"topic:{topic}" for topic in args.topic)
    query = " ".join(parts)

    client = GitHubClient(token=os.environ.get("GITHUB_TOKEN"))
    payloads = client.search_repositories(query, limit=args.limit)
    repos = [score_repository(Repository.from_api(payload)) for payload in payloads]
    repos.sort(key=lambda repo: repo.score, reverse=True)
    write_candidates(args.output, repos, query)
    snapshot = write_snapshot(args.snapshot_dir, repos)

    print(f"Wrote {len(repos)} candidates to {args.output}")
    print(f"Saved snapshot to {snapshot}")
    for number, repo in enumerate(repos[:10], 1):
        print(f"{number:>2}. {repo.score:>5.2f}  {repo.full_name}  ★ {repo.stars:,}")
    return 0


def _draft(args: argparse.Namespace) -> int:
    repos = read_candidates(args.input)
    repo = next((item for item in repos if item.full_name.casefold() == args.repo.casefold()), None)
    if not repo:
        available = ", ".join(item.full_name for item in repos[:10])
        raise ValueError(f"repository not found in candidate file. Available examples: {available}")
    path = write_draft(args.daily_dir, repo, args.date)
    print(f"Created review-required draft: {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "scan":
            return _scan(args)
        if args.command == "draft":
            return _draft(args)
        if args.command == "index":
            update_readme_index(args.readme, args.daily_dir)
            print(f"Updated index in {args.readme}")
            return 0
    except (GitHubError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

