"""GitHub Trending Crawler with fallback to Search API."""

import base64
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import httpx
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .config import get_settings


@dataclass
class Repository:
    """Data class for a GitHub repository."""

    name: str  # owner/repo format
    url: str
    description: str
    stars: int
    language: str
    readme_content: str = ""
    stars_today: int = 0

    @property
    def owner(self) -> str:
        return self.name.split("/")[0]

    @property
    def repo_name(self) -> str:
        return self.name.split("/")[1]


@dataclass
class CrawlerResult:
    """Result of crawling operation."""

    repos: list[Repository] = field(default_factory=list)
    source: str = "trending"  # "trending" or "search_api"
    crawled_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class GitHubCrawler:
    """Crawler for GitHub trending repositories with API fallback."""

    TRENDING_URL = "https://github.com/trending"
    API_BASE = "https://api.github.com"

    def __init__(self):
        self.settings = get_settings()
        self.ua = UserAgent()
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Lazy-loaded HTTP client."""
        if self._client is None:
            headers = {"User-Agent": self.ua.random}
            if self.settings.github_token:
                headers["Authorization"] = (
                    f"token {self.settings.github_token.get_secret_value()}"
                )
            self._client = httpx.Client(headers=headers, timeout=30.0, follow_redirects=True)
        return self._client

    def close(self):
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        before_sleep=lambda retry_state: logger.warning(
            f"Retry attempt {retry_state.attempt_number} after error"
        ),
    )
    def _fetch_trending_page(self) -> str:
        """Fetch GitHub trending page HTML."""
        params = {}
        if self.settings.trending_language:
            params["spoken_language_code"] = ""
            # Language is part of the URL path, not query params
            url = f"{self.TRENDING_URL}/{self.settings.trending_language}"
        else:
            url = self.TRENDING_URL

        if self.settings.trending_since != "daily":
            params["since"] = self.settings.trending_since

        # Rotate User-Agent on each request
        self.client.headers["User-Agent"] = self.ua.random

        response = self.client.get(url, params=params)
        response.raise_for_status()
        return response.text

    def _parse_trending_html(self, html: str) -> list[Repository]:
        """Parse trending page HTML into Repository objects."""
        soup = BeautifulSoup(html, "lxml")
        repos = []

        for article in soup.select("article.Box-row"):
            try:
                # Repository name (owner/repo)
                name_elem = article.select_one("h2 a")
                if not name_elem:
                    continue
                name = name_elem.get("href", "").strip("/")
                if not name or "/" not in name:
                    continue

                # URL
                url = f"https://github.com/{name}"

                # Description
                desc_elem = article.select_one("p")
                description = desc_elem.get_text(strip=True) if desc_elem else ""

                # Stars (total)
                stars = 0
                stars_elem = article.select_one('a[href$="/stargazers"]')
                if stars_elem:
                    stars_text = stars_elem.get_text(strip=True).replace(",", "")
                    stars = int(stars_text) if stars_text.isdigit() else 0

                # Language
                lang_elem = article.select_one('[itemprop="programmingLanguage"]')
                language = lang_elem.get_text(strip=True) if lang_elem else "Unknown"

                # Stars today
                stars_today = 0
                today_elem = article.select_one("span.d-inline-block.float-sm-right")
                if today_elem:
                    today_text = today_elem.get_text(strip=True)
                    # Format: "1,234 stars today"
                    stars_today_str = today_text.split()[0].replace(",", "")
                    if stars_today_str.isdigit():
                        stars_today = int(stars_today_str)

                repos.append(
                    Repository(
                        name=name,
                        url=url,
                        description=description,
                        stars=stars,
                        language=language,
                        stars_today=stars_today,
                    )
                )

            except Exception as e:
                logger.warning(f"Failed to parse repo element: {e}")
                continue

        return repos[: self.settings.max_repos]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    )
    def _fetch_via_search_api(self) -> list[Repository]:
        """Fallback: Use GitHub Search API for recent popular repos."""
        logger.info("Using GitHub Search API as fallback...")

        # Search for repos created in last 7 days, sorted by stars
        since_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        query = f"created:>{since_date}"
        if self.settings.trending_language:
            query += f" language:{self.settings.trending_language}"

        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": self.settings.max_repos,
        }

        response = self.client.get(f"{self.API_BASE}/search/repositories", params=params)
        response.raise_for_status()
        data = response.json()

        repos = []
        for item in data.get("items", []):
            repos.append(
                Repository(
                    name=item["full_name"],
                    url=item["html_url"],
                    description=item.get("description") or "",
                    stars=item.get("stargazers_count", 0),
                    language=item.get("language") or "Unknown",
                    stars_today=0,  # API doesn't provide this
                )
            )

        return repos

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((httpx.HTTPError,)),
    )
    def _fetch_readme(self, repo: Repository) -> str:
        """Fetch README content for a repository."""
        try:
            # Try API endpoint for README
            response = self.client.get(
                f"{self.API_BASE}/repos/{repo.name}/readme",
                headers={"Accept": "application/vnd.github.v3+json"},
            )

            if response.status_code == 200:
                data = response.json()
                content = data.get("content", "")
                if content:
                    # Decode base64 content
                    return base64.b64decode(content).decode("utf-8", errors="ignore")

            # Fallback: try raw URL
            for readme_name in ["README.md", "readme.md", "README", "readme.rst"]:
                raw_url = f"https://raw.githubusercontent.com/{repo.name}/HEAD/{readme_name}"
                resp = self.client.get(raw_url)
                if resp.status_code == 200:
                    return resp.text

        except Exception as e:
            logger.debug(f"Failed to fetch README for {repo.name}: {e}")

        return ""

    def crawl(self, fetch_readme: bool = True) -> CrawlerResult:
        """
        Crawl GitHub trending repositories.

        Args:
            fetch_readme: Whether to fetch README content for each repo.

        Returns:
            CrawlerResult with list of repositories and metadata.
        """
        result = CrawlerResult()

        # Try scraping trending page first
        try:
            logger.info("Fetching GitHub Trending page...")
            html = self._fetch_trending_page()
            repos = self._parse_trending_html(html)

            if repos:
                result.repos = repos
                result.source = "trending"
                logger.success(f"Found {len(repos)} trending repositories")
            else:
                raise ValueError("No repos parsed from trending page")

        except Exception as e:
            logger.warning(f"Trending page scrape failed: {e}")
            logger.info("Falling back to Search API...")

            try:
                result.repos = self._fetch_via_search_api()
                result.source = "search_api"
                logger.success(f"Found {len(result.repos)} repositories via Search API")
            except Exception as api_error:
                logger.error(f"Search API also failed: {api_error}")
                raise RuntimeError("All crawling methods failed") from api_error

        # Fetch README for each repo
        if fetch_readme and result.repos:
            logger.info("Fetching README files...")
            for i, repo in enumerate(result.repos):
                logger.debug(f"[{i + 1}/{len(result.repos)}] Fetching README for {repo.name}")
                repo.readme_content = self._fetch_readme(repo)

        return result


def crawl_trending() -> CrawlerResult:
    """Convenience function to crawl trending repos."""
    with GitHubCrawler() as crawler:
        return crawler.crawl()
