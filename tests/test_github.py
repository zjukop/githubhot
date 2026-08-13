import unittest
from unittest.mock import patch

from githubhot.github import GitHubClient, summarize_readme


class ReadmeSummaryTests(unittest.TestCase):
    def test_extracts_summary_features_and_quick_start(self) -> None:
        markdown = """
# Useful Repo

Useful Repo is a local-first developer tool that creates reproducible reports from source repositories.

## Features

- Runs locally without uploading source code
- Exports a shareable Markdown report

## Quick Start

```bash
python -m useful_repo scan .
```
"""
        summary, features, quick_start = summarize_readme(markdown)
        self.assertIn("local-first developer tool", summary)
        self.assertEqual(len(features), 2)
        self.assertEqual(quick_start, "python -m useful_repo scan .")

    def test_ignores_badges_and_images(self) -> None:
        markdown = """
# Tool

![screenshot](image.png)
[![build](badge.svg)](actions)

This paragraph explains the actual project purpose in enough detail to become the selected summary.
"""
        summary, features, _ = summarize_readme(markdown)
        self.assertIn("actual project purpose", summary)
        self.assertEqual(features, [])

    def test_does_not_treat_build_dependencies_as_features(self) -> None:
        markdown = """
# Tool

Tool provides a detailed and useful description of its purpose for software developers.

## Building

- Rust toolchain is required
- protoc is required
"""
        _, features, _ = summarize_readme(markdown)
        self.assertEqual(features, [])

    def test_ignores_empty_package_links_as_summary(self) -> None:
        markdown = """
# Tool

[](https://pypi.org/project/tool/) [](https://npmjs.com/tool)

Tool converts many document formats to clean Markdown locally without external services.
"""
        summary, _, _ = summarize_readme(markdown)
        self.assertIn("converts many document formats", summary)


class TrendingFallbackTests(unittest.TestCase):
    @patch.object(GitHubClient, "_request")
    @patch("urllib.request.urlopen")
    def test_resolves_trending_repository_entries(self, urlopen, api_request) -> None:
        response = urlopen.return_value.__enter__.return_value
        response.read.return_value = b'''<article><h2><a href="/owner/tool">tool</a></h2>
        <a href="/owner/tool/stargazers">stars</a></article>'''
        api_request.return_value = {"full_name": "owner/tool"}

        repos = GitHubClient().trending_repositories(limit=10)

        self.assertEqual(repos, [{"full_name": "owner/tool"}])
        api_request.assert_called_once_with("/repos/owner/tool")


if __name__ == "__main__":
    unittest.main()
