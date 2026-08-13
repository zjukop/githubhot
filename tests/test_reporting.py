import tempfile
import unittest
from datetime import date
from pathlib import Path

from githubhot.models import Repository
from githubhot.reporting import render_digest, render_draft, update_readme_index, write_draft


def repo() -> Repository:
    return Repository(
        full_name="owner/useful-repo",
        html_url="https://github.com/owner/useful-repo",
        description="A useful tool",
        stars=1200,
        forks=100,
        open_issues=12,
        watchers=30,
        language="Python",
        license="MIT",
        topics=["developer-tools"],
        created_at="2026-07-01T00:00:00Z",
        updated_at="2026-08-12T00:00:00Z",
        pushed_at="2026-08-12T00:00:00Z",
        score=80,
        score_reasons=["fast growth"],
    )


class ReportingTests(unittest.TestCase):
    def test_draft_contains_review_guards(self) -> None:
        content = render_draft(repo(), date(2026, 8, 13))
        self.assertIn("TODO", content)
        self.assertIn("不构成质量或安全背书", content)

    def test_index_uses_generated_article(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            readme = root / "README.md"
            readme.write_text("before\n<!-- DAILY_INDEX_START -->\nold\n<!-- DAILY_INDEX_END -->\nafter\n", encoding="utf-8")
            path = write_draft(root / "daily", repo(), date(2026, 8, 13))
            update_readme_index(readme, root / "daily")
            content = readme.read_text(encoding="utf-8")
            self.assertIn(path.relative_to(root).as_posix(), content)
            self.assertIn("owner/useful-repo", content)

    def test_digest_is_publishable_and_evidence_only(self) -> None:
        content = render_digest([repo()], "created:>=2026-07-01", date(2026, 8, 13))
        self.assertNotIn("TODO", content)
        self.assertIn("GitHubHot 日报 · 2026-08-13", content)
        self.assertIn("owner/useful-repo", content)
        self.assertIn("不代表质量、安全性或投资价值", content)
        self.assertIn("../../../README.md", content)


if __name__ == "__main__":
    unittest.main()
