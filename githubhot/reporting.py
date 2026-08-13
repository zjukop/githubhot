from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from githubhot.models import Repository


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.lower().replace("/", "-")).strip("-")


def render_draft(repo: Repository, publish_date: date | None = None) -> str:
    publish_date = publish_date or date.today()
    topics = "\n".join(f"  - {topic}" for topic in repo.topics) or "  - unclassified"
    reasons = "\n".join(f"- {reason}" for reason in repo.score_reasons)
    return f"""---
repo: {repo.full_name}
date: {publish_date.isoformat()}
language: {repo.language or 'Unknown'}
stars: {repo.stars}
license: {repo.license or 'Unknown'}
topics:
{topics}
---

# {repo.full_name}

> TODO：用一句话说明它服务谁、解决什么问题，以及最关键的差异。

项目地址：[{repo.full_name}]({repo.html_url})

## 30 秒了解

- **适合谁**：TODO
- **解决什么**：{repo.description or 'TODO'}
- **核心特点**：TODO
- **使用成本**：TODO
- **成熟度**：TODO

## 为什么最近受到关注

自动采集到的候选信号（这些信号只代表关注度，不代表产品质量）：

{reasons}

TODO：核实最近的 Release、重要提交、外部传播或生态变化。无法核实的原因必须标记为推测。

## 它是怎么工作的

TODO：阅读源码和官方文档，用 3～5 个步骤解释核心机制。

## 与同类项目比较

| 项目 | 优势 | 局限 | 适合场景 |
|---|---|---|---|
| {repo.full_name} | TODO | TODO | TODO |
| TODO | TODO | TODO | TODO |

## 快速体验

```bash
# TODO：仅保留经过实际验证的官方安装/运行命令
```

## 我认为它真正有价值的地方

TODO：加入 README 中没有的技术判断。

## 局限和风险

- TODO：维护与成熟度
- TODO：安全与隐私
- TODO：成本或平台依赖

## 可以继续开发的机会

1. TODO：来自重复 Issue 的二阶工具机会
2. TODO：缺失的平台、集成或迁移能力
3. TODO：维护者明确不准备纳入主项目的需求

## 参考资料

- [官方仓库]({repo.html_url})
- TODO：官方文档
- TODO：相关 Release
- TODO：相关 Issue 或 Discussion

> 本文由自动化工具准备资料、人工选择并审核发布。数据快照仅用于发现候选，不构成质量或安全背书。
"""


def write_draft(root: Path, repo: Repository, publish_date: date | None = None) -> Path:
    publish_date = publish_date or date.today()
    directory = root / str(publish_date.year) / f"{publish_date.month:02d}"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{publish_date.isoformat()}-{_slug(repo.full_name)}.md"
    path.write_text(render_draft(repo, publish_date), encoding="utf-8")
    return path


def render_digest(
    repos: list[Repository],
    query: str,
    publish_date: date | None = None,
) -> str:
    """Render an evidence-only daily ranking that is safe to publish automatically."""
    publish_date = publish_date or date.today()
    rows = []
    details = []
    for rank, repo in enumerate(repos, 1):
        rows.append(
            f"| {rank} | [{repo.full_name}]({repo.html_url}) | {repo.score:.2f} | "
            f"{repo.stars:,} | {repo.language or 'Unknown'} | {repo.license or 'Unknown'} |"
        )
        reasons = "；".join(repo.score_reasons)
        topics = "、".join(repo.topics[:8]) or "未标注"
        official_summary = repo.readme_summary or repo.description or "官方仓库暂未提供可提取的项目简介。"
        features = (
            "\n".join(f"- {item}" for item in repo.readme_features)
            if repo.readme_features
            else "- 官方 README 暂未提取到结构化功能列表。"
        )
        quick_start = (
            f"```bash\n{repo.quick_start}\n```"
            if repo.quick_start
            else "官方 README 暂未提取到明确的快速开始命令，请进入项目文档确认。"
        )
        release = (
            f"[{repo.latest_release_name}]({repo.latest_release_url})，发布于 {repo.latest_release_at[:10]}"
            if repo.latest_release_name and repo.latest_release_url and repo.latest_release_at
            else "尚未发现 GitHub Release，或项目使用其他方式发布版本。"
        )
        official_links = [f"[仓库]({repo.html_url})"]
        if repo.homepage:
            official_links.append(f"[项目主页]({repo.homepage})")
        if repo.readme_url:
            official_links.append(f"[README]({repo.readme_url})")
        details.append(
            f"### {rank}. [{repo.full_name}]({repo.html_url})\n\n"
            f"#### 项目介绍\n\n{official_summary}\n\n"
            f"> 以上简介提取自项目官方 README；若 README 使用英文，则保留原文以避免自动翻译造成事实偏差。\n\n"
            f"#### 核心能力\n\n{features}\n\n"
            f"#### 快速开始\n\n{quick_start}\n\n"
            f"#### 近期版本\n\n{release}\n\n"
            f"#### 项目画像\n\n"
            f"- **候选分数**：{repo.score:.2f}\n"
            f"- **Stars / Forks / Open Issues**：{repo.stars:,} / {repo.forks:,} / {repo.open_issues:,}\n"
            f"- **语言 / License**：{repo.language or 'Unknown'} / {repo.license or 'Unknown'}\n"
            f"- **Topics**：{topics}\n"
            f"- **入选信号**：{reasons}\n"
            f"- **官方资料**：{' · '.join(official_links)}\n\n"
            f"#### 阅读建议\n\n"
            f"- 核对 README 中的安装前提和平台限制；\n"
            f"- 结合 Open Issues 判断成熟度，而不是只看 Stars；\n"
            f"- 生产采用前检查许可证、最近提交和安全说明。\n"
        )

    table = "\n".join(rows) if rows else "| - | 今日没有符合条件的候选 | - | - | - | - |"
    detail_text = "\n".join(details) if details else "今日没有符合扫描条件的候选仓库。"
    return f"""# GitHubHot 日报 · {publish_date.isoformat()}

> 自动扫描近期快速增长的 GitHub 仓库。本页展示的是关注度候选，不代表质量、安全性或投资价值。

## 今日概览

- **生成日期**：{publish_date.isoformat()}
- **候选数量**：{len(repos)}
- **扫描条件**：`{query}`
- **排序依据**：Star 规模、按仓库年龄估算的增长速度、参与度、提交新鲜度、许可证与描述完整度

| # | Repository | Score | Stars | Language | License |
|---:|---|---:|---:|---|---|
{table}

## 项目详情

{detail_text}
## 数据说明

- 数据来自 GitHub 公共 API，数值是生成当时的快照；
- GitHub 搜索接口不提供历史 Star 数，当前增长速度按 Stars 与仓库年龄估算；
- 后续积累的每日快照将用于计算真实的 1/7/30 日变化；
- 项目介绍、功能和快速开始内容提取自官方 README，不自动推断项目流行原因；
- 深度介绍仍需人工阅读源码、文档、Release 和 Issues 后发布。

---

由 [GitHubHot](../../../README.md) 自动生成。
"""


def write_digest(
    root: Path,
    repos: list[Repository],
    query: str,
    publish_date: date | None = None,
) -> Path:
    publish_date = publish_date or date.today()
    directory = root / str(publish_date.year) / f"{publish_date.month:02d}"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{publish_date.isoformat()}.md"
    path.write_text(render_digest(repos, query, publish_date), encoding="utf-8")
    return path


def update_readme_index(readme: Path, daily_root: Path) -> None:
    start = "<!-- DAILY_INDEX_START -->"
    end = "<!-- DAILY_INDEX_END -->"
    content = readme.read_text(encoding="utf-8")
    if start not in content or end not in content:
        raise ValueError("README is missing daily index markers")

    articles = sorted(daily_root.glob("**/*.md"), reverse=True)
    lines = []
    for article in articles:
        relative = article.relative_to(readme.parent).as_posix()
        title = next(
            (line.removeprefix("# ").strip() for line in article.read_text(encoding="utf-8").splitlines() if line.startswith("# ")),
            article.stem,
        )
        lines.append(f"- [{article.stem[:10]} · {title}]({relative})")
    index = "\n".join(lines) if lines else "- 暂无已发布内容"
    before, remainder = content.split(start, 1)
    _, after = remainder.split(end, 1)
    readme.write_text(f"{before}{start}\n{index}\n{end}{after}", encoding="utf-8")
