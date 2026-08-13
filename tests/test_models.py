import unittest

from githubhot.models import Repository


class RepositoryTests(unittest.TestCase):
    def test_from_api_normalizes_optional_fields(self) -> None:
        repo = Repository.from_api(
            {
                "full_name": "owner/repo",
                "html_url": "https://github.com/owner/repo",
                "description": None,
                "stargazers_count": 10,
                "forks_count": 2,
                "open_issues_count": 1,
                "watchers_count": 10,
                "language": None,
                "license": None,
                "topics": None,
                "created_at": "2026-08-01T00:00:00Z",
                "updated_at": "2026-08-12T00:00:00Z",
                "pushed_at": "2026-08-12T00:00:00Z",
            }
        )

        self.assertEqual(repo.description, "")
        self.assertEqual(repo.license, None)
        self.assertEqual(repo.topics, [])


if __name__ == "__main__":
    unittest.main()

