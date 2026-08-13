from __future__ import annotations

import re
import urllib.parse
from datetime import date
from pathlib import Path

from githubhot.models import Repository


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.lower().replace("/", "-")).strip("-")


def _badge(label: str, message: str | int, color: str) -> str:
    encoded_label = urllib.parse.quote(label, safe="")
    encoded_message = urllib.parse.quote(str(message).replace("-", "--"), safe="")
    return f"![{label}](https://img.shields.io/badge/{encoded_label}-{encoded_message}-{color}?style=flat-square)"


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
        analysis = repo.analysis
        if analysis:
            positioning = analysis["positioning"]
            target_users = "\n".join(f"- {item}" for item in analysis["target_users"])
            core_capabilities = "\n".join(f"- {item}" for item in analysis["core_capabilities"])
            technical_analysis = "\n".join(f"- {item}" for item in analysis["technical_analysis"])
            why_it_matters = "\n".join(f"- {item}" for item in analysis["why_it_matters"])
            limitations = "\n".join(f"- {item}" for item in analysis["limitations"])
            opportunities = "\n".join(f"- {item}" for item in analysis["opportunities"])
            maturity = analysis["maturity"]
        else:
            positioning = "中文深度分析本次未生成，以下保留官方 README 事实资料，避免以未经验证的内容补位。"
            target_users = "- 暂无可靠的中文场景分析。"
            core_capabilities = features
            technical_analysis = "- 当前仅能确认主要语言、许可证和官方运行说明，更多架构信息需阅读源码。"
            why_it_matters = "- 该项目因近期活跃度和关注度进入候选，但热度不等于质量。"
            limitations = "- 采用前需要自行核实平台限制、安全边界、维护状态和生产成熟度。"
            opportunities = "- 需要结合 Issues 和 Discussions 验证真实痛点后再形成开发机会。"
            maturity = "本次缺少模型分析，仅展示 Stars、Issues、Release 和更新时间等客观信号。"
        anchor = _slug(repo.full_name)
        badges = " ".join(
            [
                _badge("Rank", f"#{rank}", "ff6b6b"),
                _badge("Score", f"{repo.score:.1f}", "7c3aed"),
                _badge("Stars", f"{repo.stars:,}", "f5a623"),
                _badge("Language", repo.language or "Unknown", "2563eb"),
                _badge("License", repo.license or "Unknown", "16a34a"),
            ]
        )
        target_preview = analysis["target_users"][0] if analysis else "需要进一步核实目标用户。"
        value_preview = analysis["core_capabilities"][0] if analysis else official_summary
        attention_preview = analysis["why_it_matters"][0] if analysis else "近期关注度和仓库活跃度较高。"
        risk_preview = analysis["limitations"][0] if analysis else "采用前请核实成熟度和安全边界。"
        details.append(
            f"<a id=\"{anchor}\"></a>\n\n"
            f"## {rank}. [{repo.full_name}]({repo.html_url})\n\n"
            f"{badges}\n\n"
            f"> **一句话定位**\n>\n> {positioning}\n\n"
            f"### 🧭 30 秒速读\n\n"
            f"| 维度 | 结论 |\n|---|---|\n"
            f"| 👥 **适合谁** | {target_preview} |\n"
            f"| ✨ **核心价值** | {value_preview} |\n"
            f"| 🔥 **关注理由** | {attention_preview} |\n"
            f"| ⚠️ **采用提醒** | {risk_preview} |\n\n"
            f"<details open>\n<summary><strong>👥 使用场景与核心价值</strong></summary>\n\n"
            f"#### 适合谁、用在什么场景\n\n{target_users}\n\n"
            f"#### 核心能力与价值\n\n{core_capabilities}\n\n</details>\n\n"
            f"<details>\n<summary><strong>🧩 技术实现与关注价值</strong></summary>\n\n"
            f"#### 技术实现观察\n\n{technical_analysis}\n\n"
            f"#### 为什么值得关注\n\n{why_it_matters}\n\n</details>\n\n"
            f"<details>\n<summary><strong>🚦 成熟度、局限与采用风险</strong></summary>\n\n"
            f"#### 成熟度判断\n\n{maturity}\n\n"
            f"#### 局限与采用风险\n\n{limitations}\n\n</details>\n\n"
            f"<details>\n<summary><strong>💡 可延伸的开发机会</strong></summary>\n\n"
            f"{opportunities}\n\n</details>\n\n"
            f"<details>\n<summary><strong>🚀 快速开始、版本与事实依据</strong></summary>\n\n"
            f"#### 快速开始\n\n{quick_start}\n\n"
            f"#### 近期版本\n\n{release}\n\n"
            f"#### 事实依据\n\n"
            f"- **官方简介**：{official_summary}\n"
            f"- **Stars / Forks / Open Issues**：{repo.stars:,} / {repo.forks:,} / {repo.open_issues:,}\n"
            f"- **Topics**：{topics}\n"
            f"- **入选信号**：{reasons}\n"
            f"- **官方资料**：{' · '.join(official_links)}\n\n</details>\n\n"
            f"[⬆️ 返回今日榜单](#今日榜单)\n\n---\n"
        )

    table = "\n".join(rows) if rows else "| - | 今日没有符合条件的候选 | - | - | - | - |"
    detail_text = "\n".join(details) if details else "今日没有符合扫描条件的候选仓库。"
    project_links = "\n".join(
        f"{index}. [{repo.full_name}](#{_slug(repo.full_name)})" for index, repo in enumerate(repos, 1)
    )
    return f"""<div align="center">

# 🔥 GitHubHot 日报

### {publish_date.isoformat()} · 今日值得关注的开源项目

{_badge('Daily', publish_date.isoformat(), 'e11d48')} {_badge('Projects', len(repos), '0ea5e9')} {_badge('Language', '中文深度分析', '8b5cf6')}

</div>

> [!NOTE]
> 自动扫描近期快速增长的 GitHub 仓库，再基于官方资料生成中文分析。热度是发现信号，不代表质量、安全性或投资价值。

## 📌 今日导读

| 📅 日期 | 📦 项目数 | 🔎 扫描条件 |
|---|---:|---|
| {publish_date.isoformat()} | {len(repos)} | `{query}` |

<a id="今日榜单"></a>

## 🏆 今日榜单

| # | Repository | Score | Stars | Language | License |
|---:|---|---:|---:|---|---|
{table}

> 点击下方项目名称直达分析；技术、风险和机会等长内容可按需展开。

{project_links}

---

## 📚 深度分析

{detail_text}
## ℹ️ 数据与分析说明

- 数据来自 GitHub 公共 API，数值是生成当时的快照；
- GitHub 搜索接口不提供历史 Star 数，当前增长速度按 Stars 与仓库年龄估算；
- 后续积累的每日快照将用于计算真实的 1/7/30 日变化；
- 中文分析由可配置模型基于官方 README、Release 和仓库元数据生成，也可由人工编辑稿校订；
- 模型不得补充输入中没有的事实；推断使用“可能”等限定语，仍需读者结合官方资料判断；
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
