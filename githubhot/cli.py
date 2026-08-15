from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

from githubhot.github import GitHubClient, GitHubError, summarize_readme
from githubhot.analysis import AnalysisError, GitHubModelsClient, OpenAICompatibleClient
from githubhot.models import Repository
from githubhot.reporting import update_readme_index, write_deep_dive, write_digest, write_draft
from githubhot.scoring import score_repository
from githubhot.social import SocialPublishError, WeChatDraftClient, record_delivery, render_wechat_draft, write_social_drafts
from githubhot.storage import read_candidate_payload, read_candidates, write_candidates, write_snapshot


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
    scan.add_argument("--enrich", type=int, default=10, help="Fetch README and latest release for top N candidates")
    scan.add_argument("--enrich-workers", type=int, default=5, help="Concurrent README and release requests")
    scan.add_argument("--analyze", type=int, default=0, help="Generate Chinese deep analysis for top N candidates")
    scan.add_argument("--model", default=os.environ.get("ANALYSIS_MODEL") or "deepseek-v4-flash", help="Analysis model ID")
    scan.add_argument("--analysis-provider", choices=("openai", "github"), default="openai")
    scan.add_argument("--min-analysis-rate", type=float, default=0.8, help="Fail when fewer analyzed repos than this ratio (0-1)")
    scan.add_argument("--analysis-workers", type=int, default=3, help="Concurrent analysis requests")

    draft = subparsers.add_parser("draft", help="Create a human-review article draft")
    draft.add_argument("repo", help="Repository full name from the candidate list")
    draft.add_argument("--input", type=Path, default=Path("data/candidates.json"))
    draft.add_argument("--daily-dir", type=Path, default=Path("daily"))
    draft.add_argument("--date", type=date.fromisoformat, default=date.today())

    digest = subparsers.add_parser("digest", help="Publish an evidence-only daily ranking")
    digest.add_argument("--input", type=Path, default=Path("data/candidates.json"))
    digest.add_argument("--daily-dir", type=Path, default=Path("daily"))
    digest.add_argument("--readme", type=Path, default=Path("README.md"))
    digest.add_argument("--top", type=int, default=10)
    digest.add_argument("--date", type=date.fromisoformat, default=date.today())
    digest.add_argument("--editorial-dir", type=Path, default=Path("data/editorial"))
    digest.add_argument("--deep-dive-dir", type=Path, default=Path("deep-dives"))

    index = subparsers.add_parser("index", help="Regenerate README daily article index")
    index.add_argument("--readme", type=Path, default=Path("README.md"))
    index.add_argument("--daily-dir", type=Path, default=Path("daily"))

    syndicate = subparsers.add_parser("syndicate", help="Adapt the daily briefing for social platform drafts")
    syndicate.add_argument("--input", type=Path, default=Path("data/candidates.json"))
    syndicate.add_argument("--output-dir", type=Path, default=Path(".local/social-drafts"))
    syndicate.add_argument("--top", type=int, default=3)
    syndicate.add_argument("--date", type=date.fromisoformat, default=date.today())
    syndicate.add_argument(
        "--cover",
        type=Path,
        default=Path("assets/cyber-carpenter-wechat-cover-v3.png"),
        help="Reusable cover image for WeChat and Xiaohongshu drafts",
    )
    syndicate.add_argument(
        "--wechat-media-cache",
        type=Path,
        default=Path(".local/wechat-thumb-media-id"),
        help="Local cache for the permanent WeChat cover media_id",
    )
    syndicate.add_argument(
        "--source-base-url",
        default="https://github.com/zjukop/githubhot/blob/main",
        help="Public base URL used for links back to the full daily briefing",
    )
    syndicate.add_argument("--publish-wechat", action="store_true", help="Create a WeChat Official Account draft")
    syndicate.add_argument(
        "--publish-wechat-if-configured",
        action="store_true",
        help="Create a WeChat draft when all required environment variables are available",
    )
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
    try:
        payloads = client.search_repositories(query, limit=args.limit)
    except GitHubError as exc:
        if "flagged as spammy" not in str(exc):
            raise
        print("GitHub Search is account-restricted; falling back to GitHub Trending.", file=sys.stderr)
        payloads = client.trending_repositories(limit=args.limit)
        query = "GitHub Trending · daily（Search API 账号限制时的自动降级数据源）"
    repos = [score_repository(Repository.from_api(payload)) for payload in payloads]
    repos.sort(key=lambda repo: repo.score, reverse=True)
    if args.enrich_workers < 1:
        raise ValueError("enrich-workers must be positive")

    def enrich_repo(repo: Repository) -> tuple[Repository, tuple[str, str] | None, dict[str, object] | None, GitHubError | None]:
        try:
            readme = client.repository_readme(repo.full_name)
            release = client.latest_release(repo.full_name)
            return repo, readme, release, None
        except GitHubError as exc:
            return repo, None, None, exc

    enrich_targets = repos[: args.enrich]
    with ThreadPoolExecutor(max_workers=min(args.enrich_workers, len(enrich_targets) or 1)) as executor:
        futures = [executor.submit(enrich_repo, repo) for repo in enrich_targets]
        for future in as_completed(futures):
            repo, readme, release, error = future.result()
            if error:
                repo.score_reasons.append(f"detail collection unavailable: {error}")
                continue
            if readme:
                markdown, repo.readme_url = readme
                repo.readme_summary, repo.readme_features, repo.quick_start = summarize_readme(markdown)
            if release:
                repo.latest_release_name = release.get("name") or release.get("tag_name")
                repo.latest_release_url = release.get("html_url")
                repo.latest_release_at = release.get("published_at")
    if args.analyze:
        token = (os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("ANALYSIS_API_KEY")) if args.analysis_provider == "openai" else os.environ.get("GITHUB_TOKEN")
        if not token:
            required = "DEEPSEEK_API_KEY" if args.analysis_provider == "openai" else "GITHUB_TOKEN"
            raise ValueError(f"{required} is required when --analyze is enabled")
        if args.analysis_provider == "openai":
            analyst = OpenAICompatibleClient(
                token=token,
                model=args.model,
                endpoint=os.environ.get("ANALYSIS_BASE_URL") or "https://api.deepseek.com/chat/completions",
            )
        else:
            analyst = GitHubModelsClient(token=token, model=args.model)
        if args.analysis_workers < 1:
            raise ValueError("analysis-workers must be positive")
        targets = repos[: args.analyze]

        def analyze_repo(repo: Repository) -> tuple[Repository, dict[str, object] | AnalysisError]:
            try:
                return repo, analyst.analyze(repo)
            except AnalysisError as exc:
                return repo, exc

        with ThreadPoolExecutor(max_workers=min(args.analysis_workers, len(targets) or 1)) as executor:
            futures = [executor.submit(analyze_repo, repo) for repo in targets]
            for future in as_completed(futures):
                repo, result = future.result()
                if isinstance(result, AnalysisError):
                    repo.score_reasons.append(f"Chinese analysis unavailable: {result}")
                else:
                    repo.analysis = result
        requested = len(targets)
        completed = sum(bool(repo.analysis) for repo in repos[:requested])
        analysis_rate = completed / requested if requested else 1.0
        if not 0 <= args.min_analysis_rate <= 1:
            raise ValueError("min-analysis-rate must be between 0 and 1")
        if analysis_rate < args.min_analysis_rate:
            raise ValueError(
                f"Chinese analysis success rate {completed}/{requested} ({analysis_rate:.0%}) "
                f"is below required {args.min_analysis_rate:.0%}; refusing to publish"
            )
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
        if args.command == "digest":
            if args.top < 1:
                raise ValueError("top must be positive")
            query, repos = read_candidate_payload(args.input)
            editorial_path = args.editorial_dir / f"{args.date.isoformat()}.json"
            if editorial_path.exists():
                editorial = json.loads(editorial_path.read_text(encoding="utf-8"))
                for repo in repos:
                    if repo.full_name in editorial:
                        repo.analysis = editorial[repo.full_name]
            path = write_digest(args.daily_dir, repos[: args.top], query, args.date)
            if repos:
                deep_dive_path = write_deep_dive(args.deep_dive_dir, repos[0], args.date)
                print(f"Published featured deep dive: {deep_dive_path}")
            update_readme_index(args.readme, args.daily_dir)
            print(f"Published daily digest: {path}")
            return 0
        if args.command == "index":
            update_readme_index(args.readme, args.daily_dir)
            print(f"Updated index in {args.readme}")
            return 0
        if args.command == "syndicate":
            if args.top < 1:
                raise ValueError("top must be positive")
            repos = read_candidates(args.input)[: args.top]
            source_url = (
                f"{args.source_base_url.rstrip('/')}/daily/{args.date.year}/"
                f"{args.date.month:02d}/{args.date.isoformat()}.md"
            )
            paths = write_social_drafts(args.output_dir, repos, args.date, source_url, args.cover)
            for platform, path in paths.items():
                print(f"Generated {platform} draft: {path}")
            configured = all(os.environ.get(name) for name in ("WECHAT_APP_ID", "WECHAT_APP_SECRET"))
            should_publish = args.publish_wechat or (args.publish_wechat_if_configured and configured)
            if should_publish:
                draft = render_wechat_draft(repos, args.date, source_url)
                client = WeChatDraftClient.from_environment()
                thumb_media_id = client.resolve_thumb_media_id(args.cover, args.wechat_media_cache)
                media_id = client.add_draft(draft, thumb_media_id)
                record_delivery(paths["manifest"], "wechat", "drafted", media_id=media_id)
                print(f"Created WeChat draft: {media_id}")
            elif args.publish_wechat_if_configured:
                print("WeChat draft skipped: configuration is incomplete", file=sys.stderr)
            return 0
    except (GitHubError, OSError, SocialPublishError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
