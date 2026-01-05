"""AI Summarizer using OpenAI-compatible LLM APIs."""

import json
import re
from dataclasses import dataclass, field

from loguru import logger
from openai import OpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .config import get_settings
from .crawler import Repository

# Maximum characters to send from README to LLM
MAX_README_CHARS = 2000


SYSTEM_PROMPT = """你是一个专业的技术博主和开源项目分析师。你的任务是分析 GitHub 项目并生成简洁、有洞察力的中文总结。

分析时请关注：
1. 项目解决了什么核心问题
2. 技术亮点和创新点
3. 目标用户群体
4. 项目成熟度和活跃度

请严格按照以下 JSON 格式返回（不要包含 markdown 代码块标记）：
{
    "one_liner_cn": "一句话中文介绍（20字以内，俏皮易懂，可用emoji）",
    "core_features": [
        "核心功能1",
        "核心功能2",
        "核心功能3"
    ],
    "use_case": "适合什么人用？解决了什么痛点？（50字以内）",
    "score": 4,
    "score_reason": "评分理由（20字以内）"
}

评分标准（score 1-5）：
- 5星：革命性项目，强烈推荐
- 4星：优秀项目，值得关注
- 3星：不错的项目，特定场景有用
- 2星：一般项目，可以了解
- 1星：早期项目或小众工具"""


USER_PROMPT_TEMPLATE = """请分析以下 GitHub 项目：

**项目名称**: {name}
**GitHub 地址**: {url}
**描述**: {description}
**编程语言**: {language}
**Star 数**: {stars:,}
**今日 Star**: {stars_today}

**README 内容（截取）**:
```
{readme_truncated}
```

请用中文分析这个项目，返回规定的 JSON 格式。"""


@dataclass
class ProjectSummary:
    """AI-generated summary for a repository."""

    repo: Repository
    one_liner_cn: str = ""
    core_features: list[str] = field(default_factory=list)
    use_case: str = ""
    score: int = 3
    score_reason: str = ""
    is_top_pick: bool = False
    error: str | None = None

    def to_markdown(self) -> str:
        """Convert summary to markdown format."""
        stars_badge = "⭐" * self.score
        top_badge = "🏆 **今日精选**" if self.is_top_pick else ""

        features_md = "\n".join(f"  - {f}" for f in self.core_features)

        return f"""### [{self.repo.name}]({self.repo.url}) {top_badge}

> {self.one_liner_cn}

- **语言**: {self.repo.language} | **Stars**: {self.repo.stars:,} | **今日**: +{self.repo.stars_today}
- **推荐指数**: {stars_badge} ({self.score}/5) - {self.score_reason}

**核心功能**:
{features_md}

**适用场景**: {self.use_case}

---
"""


@dataclass
class SummaryResult:
    """Result of AI summarization."""

    top_picks: list[ProjectSummary] = field(default_factory=list)
    quick_looks: list[ProjectSummary] = field(default_factory=list)

    @property
    def all_summaries(self) -> list[ProjectSummary]:
        return self.top_picks + self.quick_looks


class AISummarizer:
    """Summarize GitHub repos using LLM."""

    def __init__(self):
        self.settings = get_settings()
        self.client = OpenAI(
            api_key=self.settings.openai_api_key.get_secret_value(),
            base_url=self.settings.openai_base_url,
        )

    def _truncate_readme(self, content: str) -> str:
        """Truncate README content to save tokens."""
        if not content:
            return "(README 内容为空)"

        # Remove images and links to save tokens
        content = re.sub(r"!\[.*?\]\(.*?\)", "", content)
        content = re.sub(r"<img[^>]*>", "", content)

        # Keep first N characters
        if len(content) > MAX_README_CHARS:
            content = content[:MAX_README_CHARS] + "\n... (内容已截断)"

        return content.strip() or "(README 内容为空)"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        before_sleep=lambda rs: logger.warning(f"LLM retry attempt {rs.attempt_number}"),
    )
    def _call_llm(self, repo: Repository) -> dict:
        """Call LLM API to get project summary."""
        user_prompt = USER_PROMPT_TEMPLATE.format(
            name=repo.name,
            url=repo.url,
            description=repo.description or "无描述",
            language=repo.language,
            stars=repo.stars,
            stars_today=repo.stars_today or "N/A",
            readme_truncated=self._truncate_readme(repo.readme_content),
        )

        response = self.client.chat.completions.create(
            model=self.settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=500,
        )

        content = response.choices[0].message.content.strip()

        # Clean up response (remove markdown code blocks if present)
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\n?", "", content)
            content = re.sub(r"\n?```$", "", content)

        return json.loads(content)

    def summarize_repo(self, repo: Repository) -> ProjectSummary:
        """Generate summary for a single repository."""
        summary = ProjectSummary(repo=repo)

        try:
            data = self._call_llm(repo)

            summary.one_liner_cn = data.get("one_liner_cn", "")
            summary.core_features = data.get("core_features", [])[:3]
            summary.use_case = data.get("use_case", "")
            summary.score = min(5, max(1, int(data.get("score", 3))))
            summary.score_reason = data.get("score_reason", "")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response for {repo.name}: {e}")
            summary.error = f"JSON parse error: {e}"
            summary.one_liner_cn = repo.description or "解析失败"
            summary.core_features = ["解析失败，请查看原项目"]

        except Exception as e:
            logger.error(f"LLM call failed for {repo.name}: {e}")
            summary.error = str(e)
            summary.one_liner_cn = repo.description or "API 调用失败"
            summary.core_features = ["API 调用失败，请稍后重试"]

        return summary

    def summarize_all(self, repos: list[Repository]) -> SummaryResult:
        """
        Summarize all repositories and categorize into top picks and quick looks.

        Selection logic for top picks:
        1. Top N from trending list (by position)
        2. OR highest stars_today growth
        """
        result = SummaryResult()

        if not repos:
            logger.warning("No repositories to summarize")
            return result

        # Determine top picks
        # Strategy: Use stars_today if available, otherwise use list position
        repos_with_growth = [r for r in repos if r.stars_today > 0]

        if repos_with_growth:
            # Sort by stars growth today
            sorted_repos = sorted(repos_with_growth, key=lambda r: r.stars_today, reverse=True)
            top_pick_repos = set(r.name for r in sorted_repos[: self.settings.top_pick_count])
        else:
            # Fall back to list position (trending order)
            top_pick_repos = set(r.name for r in repos[: self.settings.top_pick_count])

        # Generate summaries
        for i, repo in enumerate(repos):
            logger.info(f"[{i + 1}/{len(repos)}] Summarizing {repo.name}...")
            summary = self.summarize_repo(repo)
            summary.is_top_pick = repo.name in top_pick_repos

            if summary.is_top_pick:
                result.top_picks.append(summary)
            else:
                result.quick_looks.append(summary)

        # Sort top picks by score
        result.top_picks.sort(key=lambda s: (s.score, s.repo.stars_today), reverse=True)

        return result


def summarize_repos(repos: list[Repository]) -> SummaryResult:
    """Convenience function to summarize repositories."""
    summarizer = AISummarizer()
    return summarizer.summarize_all(repos)
