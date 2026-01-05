# GitHub Trending Hot (GEMINI.md)

**Project Overview**

`githubhot` is an automated pipeline that tracks trending GitHub repositories, generates AI-powered summaries, creates daily Markdown reports, and sends notifications to various platforms (Feishu, DingTalk, Slack, Telegram). It is designed to run daily via GitHub Actions but can also be executed locally.

**Architecture**

The project follows a linear pipeline architecture:

1.  **Crawler (`src/crawler.py`)**: Fetches trending repositories. It primarily attempts to scrape `github.com/trending` and falls back to the GitHub Search API if scraping fails.
2.  **Summarizer (`src/ai_summarizer.py`)**: Uses an LLM (via OpenAI SDK) to generate concise summaries of the repositories, categorizing them into "Top Picks" and "Quick Looks".
3.  **Reporter (`src/reporter.py`)**: Generates a static Markdown report in the `reports/` directory.
4.  **Notifier (`src/notifier.py`)**: Broadcasts the "Top Picks" to configured webhook endpoints.

**Directory Structure**

*   `main.py`: Entry point orchestrating the entire pipeline.
*   `src/`: Core application logic.
    *   `config.py`: Configuration management using `pydantic-settings`.
    *   `crawler.py`: Scraping and API fallback logic.
    *   `ai_summarizer.py`: LLM interaction and prompt management.
    *   `notifier.py`: Multi-platform notification handlers.
    *   `reporter.py`: Markdown report generation.
*   `reports/`: output directory for daily reports (`YYYY-MM-DD.md`).
*   `.github/workflows/`: CI/CD configuration for daily automated runs.

**Setup & Installation**

1.  **Prerequisites**: Python 3.11+

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Configuration**:
    Copy `.env.example` to `.env` and fill in the required values.
    *   `OPENAI_API_KEY` (Required): API key for the LLM.
    *   `OPENAI_BASE_URL` (Optional): Custom base URL for the LLM API (e.g., for Claude or Azure).

**Usage**

*   **Run the full pipeline:**
    ```bash
    python main.py
    ```

*   **Run for a specific language:**
    ```bash
    TRENDING_LANGUAGE=python python main.py
    ```

**Configuration**

Key settings managed via environment variables (defined in `src/config.py`):

| Variable | Description | Default |
| :--- | :--- | :--- |
| `OPENAI_API_KEY` | LLM API Key | **Required** |
| `OPENAI_BASE_URL` | LLM API Base URL | `https://api.openai.com/v1` |
| `LLM_MODEL` | LLM Model Name | `gpt-4o-mini` |
| `GITHUB_TOKEN` | GitHub Token (increases API limits) | `None` |
| `TRENDING_LANGUAGE` | Filter by language (e.g., `python`, `rust`) | `""` (All) |
| `TRENDING_SINCE` | Time range (`daily`, `weekly`, `monthly`) | `daily` |
| `FEISHU_WEBHOOK_URL` | Feishu/Lark Webhook | `None` |
| `DINGTALK_WEBHOOK_URL`| DingTalk Webhook | `None` |
| `SLACK_WEBHOOK_URL` | Slack Webhook | `None` |

**Development Guidelines**

*   **Type Safety**: The project relies heavily on Python type hints and `pydantic` for data validation and settings management.
*   **HTTP Clients**: `httpx` is used for all HTTP requests. Clients are typically lazy-loaded and should be closed properly (or used as context managers).
*   **Resilience**: `tenacity` is used for retrying network operations with exponential backoff.
*   **Logging**: `loguru` is used for structured logging.

**Key Files**

*   `src/config.py`: Centralized configuration. Modify this to add new settings.
*   `src/crawler.py`: Contains the logic for parsing GitHub's HTML and the fallback API search query.
*   `CLAUDE.md`: Contains concise context and commands for AI assistants.
