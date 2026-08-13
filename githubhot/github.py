from __future__ import annotations

import json
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

