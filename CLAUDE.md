# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python main.py

# Run with specific language filter
TRENDING_LANGUAGE=python python main.py
```

## Architecture Overview

```
githubhot/
├── main.py              # Entry point - orchestrates the pipeline
├── src/
│   ├── config.py        # Pydantic settings from env vars
│   ├── crawler.py       # GitHub trending scraper + Search API fallback
│   ├── ai_summarizer.py # LLM integration for project summaries
│   ├── notifier.py      # Multi-platform webhook notifications
│   └── reporter.py      # Markdown report generator
├── reports/             # Generated daily reports (YYYY-MM-DD.md)
└── .github/workflows/   # GitHub Actions for daily automation
```

### Key Technologies
- **Language**: Python 3.11+
- **HTTP Client**: httpx (async-capable, modern API)
- **Web Scraping**: BeautifulSoup4 + lxml
- **LLM**: OpenAI SDK (compatible with Claude/Azure via base_url)
- **Config**: pydantic-settings (type-safe env loading)
- **Retry**: tenacity (exponential backoff)
- **Logging**: loguru

### Data Flow

1. **Crawler** (`crawler.py`):
   - Primary: Scrapes `github.com/trending` with random User-Agent
   - Fallback: GitHub Search API (`created:>7d sort:stars`) if scraping fails
   - Fetches README.md for each repo via API or raw.githubusercontent.com

2. **Summarizer** (`ai_summarizer.py`):
   - Truncates README to 2000 chars to save tokens
   - Calls LLM with structured prompt expecting JSON response
   - Categorizes into "top_picks" (by stars_today) and "quick_looks"

3. **Reporter** (`reporter.py`):
   - Generates `reports/YYYY-MM-DD.md` with TOC, summaries, statistics

4. **Notifier** (`notifier.py`):
   - Abstract `BaseNotifier` class with platform-specific implementations
   - Supports: Feishu, DingTalk, Slack, Telegram
   - Only sends top_picks to avoid notification spam

### Configuration

All settings via environment variables (see `.env.example`):

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | LLM API key |
| `OPENAI_BASE_URL` | No | API endpoint (default: OpenAI) |
| `GITHUB_TOKEN` | No | Increases API rate limits |
| `FEISHU_WEBHOOK_URL` | No | Feishu bot webhook |
| `DINGTALK_WEBHOOK_URL` | No | DingTalk bot webhook |
| `SLACK_WEBHOOK_URL` | No | Slack incoming webhook |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot token |

### GitHub Actions

`.github/workflows/daily_run.yml`:
- Runs daily at 08:00 UTC (cron)
- Manual trigger with optional language filter
- Secrets required: `OPENAI_API_KEY` (minimum)
- Commits reports back to repo

### Key Patterns

- **Fallback mechanism**: Crawler tries scraping first, falls back to API
- **Retry with backoff**: All HTTP calls use tenacity with exponential backoff
- **Token optimization**: README truncated before LLM call
- **Lazy initialization**: HTTP clients created on first use
- **Context managers**: Crawler supports `with` statement for cleanup
