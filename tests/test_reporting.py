import tempfile
import unittest
from datetime import date
from pathlib import Path

from githubhot.models import Repository
from githubhot.reporting import render_digest, render_draft, update_readme_index, write_draft


def repo() -> Repository:
    return Repository(
        full_name="owner/useful-repo",
        html_url="https://github.com/owner/useful-repo",
        description="A useful tool",
        stars=1200,
        forks=100,
        open_issues=12,
        watchers=30,
        language="Python",
        license="MIT",
        topics=["developer-tools"],
        created_at="2026-07-01T00:00:00Z",
        updated_at="2026-08-12T00:00:00Z",
        pushed_at="2026-08-12T00:00:00Z",
        score=80,
        score_reasons=["fast growth"],
        homepage="https://example.com",
        readme_url="https://github.com/owner/useful-repo#readme",
        readme_summary="A detailed official introduction for a useful developer tool.",
        readme_features=["Runs locally without uploading source code", "Exports a reproducible report"],
        quick_start="python -m useful_repo",
        latest_release_name="v1.0.0",
        latest_release_url="https://github.com/owner/useful-repo/releases/tag/v1.0.0",
        latest_release_at="2026-08-12T00:00:00Z",
        analysis={
            "positioning": "这是一个帮助开发者生成可复现报告的本地工具。",
            "target_users": ["需要检查代码仓库的开发者。"],
            "core_capabilities": ["读取项目并生成结构化报告。"],
            "technical_analysis": ["主要使用 Python，核心流程可在本地运行。"],
            "why_it_matters": ["从现有信息看，它减少了重复检查成本。"],
            "limitations": ["生产采用前需要验证大型仓库性能。"],
            "opportunities": ["机会假设：可以增加编辑器集成。"],
            "maturity": "已有发布记录，但关注度不能直接代表生产成熟度。",
        },
    )


class ReportingTests(unittest.TestCase):
    def test_draft_contains_review_guards(self) -> None:
        content = render_draft(repo(), date(2026, 8, 13))
        self.assertIn("TODO", content)
        self.assertIn("不构成质量或安全背书", content)

    def test_index_uses_generated_article(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            readme = root / "README.md"
            readme.write_text("before\n<!-- DAILY_INDEX_START -->\nold\n<!-- DAILY_INDEX_END -->\nafter\n", encoding="utf-8")
            path = write_draft(root / "daily", repo(), date(2026, 8, 13))
            update_readme_index(readme, root / "daily")
            content = readme.read_text(encoding="utf-8")
            self.assertIn(path.relative_to(root).as_posix(), content)
            self.assertIn("owner/useful-repo", content)

    def test_digest_is_publishable_and_evidence_only(self) -> None:
        content = render_digest([repo()], "created:>=2026-07-01", date(2026, 8, 13))
        self.assertNotIn("TODO", content)
        self.assertIn("# 🔥 GitHubHot 日报", content)
        self.assertIn("2026-08-13 · 今日值得关注的开源项目", content)
        self.assertIn("owner/useful-repo", content)
        self.assertIn("不代表质量、安全性或投资价值", content)
        self.assertIn("../../../README.md", content)
        self.assertIn("> **一句话定位**", content)
        self.assertIn("#### 核心能力与价值", content)
        self.assertIn("#### 技术实现观察", content)
        self.assertIn("#### 局限与采用风险", content)
        self.assertIn("<strong>💡 可延伸的开发机会</strong>", content)
        self.assertIn("帮助开发者生成可复现报告", content)
        self.assertIn("img.shields.io", content)
        self.assertIn("### 🧭 30 秒速读", content)
        self.assertIn("<details open>", content)
        self.assertIn("⬆️ 返回今日榜单", content)
        self.assertIn("python -m useful_repo", content)
        self.assertIn("v1.0.0", content)


if __name__ == "__main__":
    unittest.main()
