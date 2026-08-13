from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from githubhot.models import Repository


class AnalysisError(RuntimeError):
    pass


REQUIRED_FIELDS = {
    "positioning": str,
    "target_users": list,
    "core_capabilities": list,
    "technical_analysis": list,
    "why_it_matters": list,
    "limitations": list,
    "opportunities": list,
    "maturity": str,
}


@dataclass(slots=True)
class GitHubModelsClient:
    token: str
    model: str = "openai/gpt-4.1"
    endpoint: str = "https://models.github.ai/inference/chat/completions"
    timeout: int = 90

    def analyze(self, repo: Repository) -> dict[str, Any]:
        facts = {
            "repository": repo.full_name,
            "description": repo.description,
            "official_readme_summary": repo.readme_summary,
            "official_features": repo.readme_features,
            "quick_start": repo.quick_start,
            "language": repo.language,
            "license": repo.license,
            "topics": repo.topics,
            "stars": repo.stars,
            "forks": repo.forks,
            "open_issues": repo.open_issues,
            "created_at": repo.created_at,
            "pushed_at": repo.pushed_at,
            "latest_release": repo.latest_release_name,
            "latest_release_at": repo.latest_release_at,
        }
        system = (
            "你是严谨的开源项目分析师。只根据用户提供的官方仓库事实写中文分析，禁止补充未提供的事实，"
            "禁止声称项目因某事件爆火。区分事实与推断：推断必须用‘从现有信息看’或‘可能’限定。"
            "输出必须是 JSON 对象，不要 Markdown，不要代码围栏。每个列表包含 2-5 个完整中文句子。"
        )
        user = f"""分析以下 GitHub 仓库事实：
{json.dumps(facts, ensure_ascii=False, indent=2)}

返回字段：
- positioning: 80-160 字，说明它是什么、解决什么问题、与普通同类工具相比的明确特点
- target_users: 目标用户与使用场景
- core_capabilities: 核心能力及用户价值，不重复罗列名词
- technical_analysis: 从语言、本地/云端方式、集成形态、部署或运行方式分析技术特点；没有信息就明确资料不足
- why_it_matters: 为什么值得开发者关注，只能基于能力、活跃度与生态信号推断
- limitations: 成熟度、依赖、平台、安全、许可证或采用成本方面需要核实的事项
- opportunities: 围绕该项目可继续开发的工具、集成、测试、运维或体验机会；必须标注为机会假设
- maturity: 60-120 字，综合 Stars、Issues、Release、更新时间判断，但不得把 Stars 等同于质量
"""
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.2,
            "max_tokens": 1800,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2026-03-10",
                "User-Agent": "githubhot/0.2",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.load(response)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            detail = ""
            if isinstance(exc, urllib.error.HTTPError):
                detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise AnalysisError(f"GitHub Models request failed: {exc} {detail}".strip()) from exc
        try:
            result = json.loads(body["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise AnalysisError("GitHub Models returned an invalid JSON response") from exc
        validate_analysis(result)
        return result


@dataclass(slots=True)
class OpenAICompatibleClient(GitHubModelsClient):
    endpoint: str = "https://api.deepseek.com/chat/completions"

    def analyze(self, repo: Repository) -> dict[str, Any]:
        # The payload and response shape are intentionally shared with GitHub Models.
        return super().analyze(repo)


def validate_analysis(value: Any) -> None:
    if not isinstance(value, dict):
        raise AnalysisError("analysis must be a JSON object")
    for field, expected_type in REQUIRED_FIELDS.items():
        if not isinstance(value.get(field), expected_type):
            raise AnalysisError(f"analysis field {field!r} has an invalid type")
        if expected_type is list and not all(isinstance(item, str) and item.strip() for item in value[field]):
            raise AnalysisError(f"analysis field {field!r} must contain non-empty strings")
        if expected_type is str and not value[field].strip():
            raise AnalysisError(f"analysis field {field!r} cannot be empty")
