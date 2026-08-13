# GitHubHot

> One fast-growing open-source repository a day, explained in Chinese with technical context and opportunity analysis.

GitHubHot is not a mirror of GitHub Trending. It combines a transparent candidate-discovery CLI with human-selected, fact-checked daily briefs.

## Quick start

Python 3.11+ is required.

```bash
python -m githubhot scan --days 30 --min-stars 100 --limit 30
python -m githubhot draft owner/repository
python -m githubhot index
```

Set `GITHUB_TOKEN` to raise the GitHub API rate limit. Automation prepares candidates and drafts; a human must verify every article before publication.

## Principles

- Popularity is a discovery signal, not a quality score.
- Installation commands must be tested before publication.
- Unsupported explanations must be labelled as inference.
- Every brief should add technical judgment beyond the upstream README.
- Limitations, security concerns and platform dependencies are part of the review.

See the [Chinese README](README.md) for the scoring model and roadmap.

## License

[MIT](LICENSE)

