from __future__ import annotations

import json
import base64
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


class GitHubError(RuntimeError):
    pass


@dataclass(slots=True)
class GitHubClient:
    token: str | None = None
    api_url: str = "https://api.github.com"
    timeout: int = 20

    def _request(self, path: str, params: dict[str, str | int] | None = None) -> Any:
        query = urllib.parse.urlencode(params or {})
        url = f"{self.api_url}{path}{'?' + query if query else ''}"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "githubhot/0.1",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise GitHubError(f"GitHub API returned {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise GitHubError(f"Unable to reach GitHub API: {exc.reason}") from exc

    def search_repositories(
        self,
        query: str,
        *,
        sort: str = "stars",
        order: str = "desc",
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        page = 1
        while len(results) < limit:
            per_page = min(100, limit - len(results))
            payload = self._request(
                "/search/repositories",
                {"q": query, "sort": sort, "order": order, "per_page": per_page, "page": page},
            )
            items = payload.get("items", [])
            results.extend(items)
            if len(items) < per_page:
                break
            page += 1
            time.sleep(0.1)
        return results

    def repository_readme(self, full_name: str) -> tuple[str, str] | None:
        try:
            payload = self._request(f"/repos/{full_name}/readme")
        except GitHubError as exc:
            if "returned 404" in str(exc):
                return None
            raise
        content = payload.get("content", "")
        if payload.get("encoding") != "base64" or not content:
            return None
        decoded = base64.b64decode(content).decode("utf-8", errors="replace")
        return decoded, payload.get("html_url", f"https://github.com/{full_name}#readme")

    def latest_release(self, full_name: str) -> dict[str, Any] | None:
        try:
            return self._request(f"/repos/{full_name}/releases/latest")
        except GitHubError as exc:
            if "returned 404" in str(exc):
                return None
            raise


def summarize_readme(markdown: str) -> tuple[str, list[str], str]:
    """Extract conservative, source-backed details without inventing facts."""
    text = re.sub(r"<!--.*?-->", "", markdown, flags=re.DOTALL)
    text = re.sub(r"!\[[^]]*]\([^)]*\)", "", text)
    text = re.sub(r"<[^>]+>", " ", text)
    lines = [line.strip() for line in text.splitlines()]

    paragraphs: list[str] = []
    current: list[str] = []
    for line in lines:
        if not line or line.startswith(("#", "[!", "---", "```")):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        if line.startswith(("- ", "* ", "+ ", "> ")):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        cleaned = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", line)
        cleaned = re.sub(r"\[\]\([^)]*\)", "", cleaned).strip()
        if 30 <= len(cleaned) <= 600 and sum(ch.isalnum() for ch in cleaned) >= 20:
            current.append(cleaned)
    if current:
        paragraphs.append(" ".join(current))
    summary = next((p for p in paragraphs if 40 <= len(p) <= 600), "")

    features: list[str] = []
    feature_section = re.search(
        r"^#{1,4}\s+(?:features?|capabilities|highlights|why\s+\w+|what\s+it\s+does|功能|特性|核心能力|亮点).*?\n(.*?)(?=^#{1,4}\s|\Z)",
        text,
        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    feature_lines = feature_section.group(1).splitlines() if feature_section else []
    for line in feature_lines:
        line = line.strip()
        if not line.startswith(("- ", "* ", "+ ")):
            continue
        item = re.sub(r"^[-*+]\s+", "", line)
        item = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", item)
        item = re.sub(r"[*_`]", "", item).strip()
        if 15 <= len(item) <= 320 and not item.lower().startswith(("http", "badge", "sponsor")):
            features.append(item)
        if len(features) == 5:
            break

    quick_start = ""
    pattern = re.compile(
        r"^#{1,4}\s+(?:quick\s*start|getting\s*started|installation|install|usage|使用|安装|快速开始).*?\n(.*?)(?=^#{1,4}\s|\Z)",
        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if match:
        code = re.search(r"```(?:bash|sh|shell|console|\w+)?\s*\n(.*?)```", match.group(1), flags=re.DOTALL)
        if code:
            quick_start = code.group(1).strip()[:1000]
    return summary, features, quick_start
