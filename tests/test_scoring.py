import unittest
from datetime import datetime, timezone

from githubhot.models import Repository
from githubhot.scoring import score_repository


def make_repo(**overrides):
    values = {
        "full_name": "owner/repo",
        "html_url": "https://github.com/owner/repo",
        "description": "Useful developer tool",
        "stars": 1000,
        "forks": 100,
        "open_issues": 20,
        "watchers": 10,
        "language": "Python",
        "license": "MIT",
        "topics": ["developer-tools"],
        "created_at": "2026-07-13T00:00:00Z",
        "updated_at": "2026-08-12T00:00:00Z",
        "pushed_at": "2026-08-12T00:00:00Z",
    }
    values.update(overrides)
    return Repository(**values)


class ScoringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 13, tzinfo=timezone.utc)

    def test_score_is_deterministic_and_explained(self) -> None:
        repo = score_repository(make_repo(), self.now)
        self.assertGreater(repo.score, 0)
        self.assertTrue(any("stars/day" in reason for reason in repo.score_reasons))
        self.assertTrue(any("MIT" in reason for reason in repo.score_reasons))

    def test_recent_fast_growing_repo_beats_old_repo_with_same_stars(self) -> None:
        recent = score_repository(make_repo(), self.now)
        old = score_repository(make_repo(created_at="2022-01-01T00:00:00Z"), self.now)
        self.assertGreater(recent.score, old.score)


if __name__ == "__main__":
    unittest.main()

