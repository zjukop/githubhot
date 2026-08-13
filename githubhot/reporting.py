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

