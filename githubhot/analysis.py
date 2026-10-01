from __future__ import annotations

import json
import re
import time
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

LIST_FIELDS = tuple(field for field, expected_type in REQUIRED_FIELDS.items() if expected_type is list)


@dataclass(slots=True)
class GitHubModelsClient:
    token: str
    model: str = "openai/gpt-4.1"
    endpoint: str = "https://models.github.ai/inference/chat/completions"
    timeout: int = 90

    provider_name: str = "GitHub Models"
    max_attempts: int = 2

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
            "不得因为输入未包含某项资料，就断言官方没有该资料；只能写‘本次输入未提供，需进一步核实’。"
            "除 JSON 英文字段名、仓库名和必要的技术专有名词外，所有字段值必须使用简体中文，禁止输出英文句子。"
            "输出必须是紧凑 JSON 对象，不要 Markdown，不要代码围栏。每个列表包含 1-3 个简短完整中文句子。"
        )
        user = f"""分析以下 GitHub 仓库事实：
{json.dumps(facts, ensure_ascii=False, indent=2)}

返回字段：
- positioning: 60-120 字，说明它是什么、解决什么问题、与普通同类工具相比的明确特点
- target_users: 目标用户与使用场景
- core_capabilities: 核心能力及用户价值，不重复罗列名词
- technical_analysis: 从语言、本地/云端方式、集成形态、部署或运行方式分析技术特点；没有信息就明确资料不足
- why_it_matters: 为什么值得开发者关注，只能基于能力、活跃度与生态信号推断
- limitations: 成熟度、依赖、平台、安全、许可证或采用成本方面需要核实的事项
- opportunities: 围绕该项目可继续开发的工具、集成、测试、运维或体验机会；必须标注为机会假设
- maturity: 50-100 字，综合 Stars、Issues、Release、更新时间判断，但不得把 Stars 等同于质量

JSON 格式示例（字段和类型必须完全一致）：
{{"positioning":"一句完整定位","target_users":["用户与场景"],"core_capabilities":["能力与价值"],"technical_analysis":["技术观察"],"why_it_matters":["关注理由"],"limitations":["采用风险"],"opportunities":["机会假设：具体方向"],"maturity":"成熟度判断"}}
"""
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.2,
            "max_tokens": 2400,
            "response_format": {"type": "json_object"},
        }
        last_error: AnalysisError | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                body = self._complete(payload)
                result = normalize_analysis(parse_analysis_response(body))
                validate_analysis(result)
                return result
            except AnalysisError as exc:
                last_error = exc
                if attempt < self.max_attempts:
                    payload["messages"] = [
                        *payload["messages"],
                        {
                            "role": "user",
                            "content": (
                                f"上一次输出未通过质量校验：{exc}。请重新生成完整 JSON；"
                                "所有解释、判断和建议必须使用简体中文，只保留必要的英文专有名词。"
                            ),
                        },
                    ]
                    time.sleep(1)
        raise AnalysisError(f"{self.provider_name} analysis failed after {self.max_attempts} attempts: {last_error}")

    def _complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2026-03-10",
                "User-Agent": "githubhot/0.3",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.load(response)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            detail = ""
            if isinstance(exc, urllib.error.HTTPError):
                detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise AnalysisError(f"{self.provider_name} request failed: {exc} {detail}".strip()) from exc


@dataclass(slots=True)
class OpenAICompatibleClient(GitHubModelsClient):
    endpoint: str = "https://api.deepseek.com/chat/completions"
    provider_name: str = "DeepSeek"

    def _complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = {**payload, "thinking": {"type": "disabled"}}
        return super(OpenAICompatibleClient, self)._complete(payload)


def parse_analysis_response(body: dict[str, Any]) -> dict[str, Any]:
    try:
        message = body["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AnalysisError("response is missing choices[0].message") from exc
    content = message.get("content")
    if isinstance(content, dict):
        return content
    if not isinstance(content, str) or not content.strip():
        finish_reason = body.get("choices", [{}])[0].get("finish_reason", "unknown")
        reasoning_present = bool(message.get("reasoning_content"))
        raise AnalysisError(
            f"response content is empty (finish_reason={finish_reason}, reasoning_content={reasoning_present})"
        )
    cleaned = content.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                pass
        raise AnalysisError("response content is not a complete JSON object")


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
    unsupported_absence = ("官方没有", "官方未提供", "未提供贡献指南", "没有提供")
    text_values = [value["positioning"], value["maturity"]]
    text_values.extend(item for field, field_type in REQUIRED_FIELDS.items() if field_type is list for item in value[field])
    if any(phrase in text for text in text_values for phrase in unsupported_absence):
        raise AnalysisError("analysis contains an unsupported claim that official material is absent")
    combined = " ".join(text_values)
    chinese_count = len(re.findall(r"[\u4e00-\u9fff]", combined))
    latin_count = len(re.findall(r"[A-Za-z]", combined))
    if chinese_count < 80 or chinese_count / max(chinese_count + latin_count, 1) < 0.35:
        raise AnalysisError("analysis is not predominantly Chinese")


def normalize_analysis(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    normalized = dict(value)
    for field in LIST_FIELDS:
        item = normalized.get(field)
        if isinstance(item, str) and item.strip():
            normalized[field] = [item.strip()]
    return normalized
