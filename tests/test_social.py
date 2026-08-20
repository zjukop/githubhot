import json
import tempfile
import unittest
from unittest.mock import patch
from datetime import date
from pathlib import Path

from test_reporting import repo
from githubhot.social import (
    SocialPublishError,
    WeChatDraftClient,
    render_wechat_draft,
    render_x_thread,
    render_xiaohongshu_draft,
    record_delivery,
    write_social_drafts,
)
from githubhot.cli import main
from githubhot.storage import write_candidates


class SocialDraftTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repos = [repo(), repo(), repo()]
        self.day = date(2026, 8, 15)
        self.url = "https://github.com/zjukop/githubhot/blob/main/daily/2026/08/2026-08-15.md"

    def test_wechat_is_styled_html_with_source(self) -> None:
        draft = render_wechat_draft(self.repos, self.day, self.url)
        self.assertEqual(draft.format, "html")
        self.assertIn("TOP 1", draft.content)
        self.assertIn("谁会真正用", draft.content)
        self.assertIn("独立开发机会", draft.content)
        self.assertIn("采用前先看", draft.content)
        self.assertIn("background:#102a43", draft.content)
        self.assertIn("border-left:4px solid #e11d48", draft.content)
        self.assertGreaterEqual(draft.content.count("box-sizing:border-box"), 7)
        self.assertIn(self.url, draft.content)
        self.assertNotIn("<script", draft.content)

    def test_xiaohongshu_uses_short_title_and_social_structure(self) -> None:
        draft = render_xiaohongshu_draft(self.repos, self.day, self.url)
        self.assertLessEqual(len(draft.title), 20)
        self.assertIn("1️⃣", draft.content)
        self.assertIn("#独立开发", draft.content)
        self.assertNotIn(self.url, draft.content)
        self.assertLessEqual(len(draft.content), 900)

    def test_x_thread_posts_stay_bounded(self) -> None:
        draft = render_x_thread(self.repos, self.day, self.url)
        posts = draft.content.split("\n\n---\n\n")
        self.assertEqual(len(posts), 3)
        self.assertTrue(all(len(post) <= 145 for post in posts))
        self.assertNotIn(self.url, draft.content)
        self.assertTrue(all(repo_item.full_name in draft.content for repo_item in self.repos))
        self.assertEqual(draft.content.count("定位："), 3)
        self.assertEqual(draft.content.count("风险："), 3)
        self.assertEqual(draft.content.count("可做："), 3)

    def test_write_social_drafts_creates_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cover = Path(directory) / "brand.png"
            cover.write_bytes(b"png")
            paths = write_social_drafts(Path(directory), self.repos, self.day, self.url, cover)
            self.assertTrue(paths["wechat"].exists())
            self.assertEqual(paths["cover"].read_bytes(), b"png")
            manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
            self.assertEqual(manifest["platforms"]["xiaohongshu"]["delivery"], "browser_required")
            record_delivery(paths["manifest"], "wechat", "drafted", media_id="media-123")
            manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
            self.assertEqual(manifest["platforms"]["wechat"]["media_id"], "media-123")

    def test_wechat_media_id_uses_cache_before_upload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "media-id"
            cache.write_text("cached-media\n", encoding="utf-8")
            client = WeChatDraftClient("app", "secret")
            self.assertEqual(client.resolve_thumb_media_id(Path(directory) / "missing.png", cache), "cached-media")

    def test_syndicate_does_not_duplicate_recorded_wechat_draft(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidates = root / "candidates.json"
            cover = root / "cover.png"
            output = root / "drafts"
            cover.write_bytes(b"png")
            write_candidates(candidates, self.repos, "query", self.day)
            paths = write_social_drafts(output, self.repos, self.day, self.url, cover)
            record_delivery(paths["manifest"], "wechat", "drafted", media_id="existing")
            with patch.dict("os.environ", {"WECHAT_APP_ID": "app", "WECHAT_APP_SECRET": "secret"}):
                with patch.object(WeChatDraftClient, "from_environment", side_effect=AssertionError("must skip")):
                    result = main([
                        "syndicate",
                        "--input", str(candidates),
                        "--output-dir", str(output),
                        "--cover", str(cover),
                        "--date", self.day.isoformat(),
                        "--publish-wechat",
                    ])
            self.assertEqual(result, 0)

    def test_syndicate_records_wechat_api_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidates = root / "candidates.json"
            cover = root / "cover.png"
            output = root / "drafts"
            cover.write_bytes(b"png")
            write_candidates(candidates, self.repos, "query", self.day)
            client = WeChatDraftClient("app", "secret")
            with patch.dict("os.environ", {"WECHAT_APP_ID": "app", "WECHAT_APP_SECRET": "secret"}):
                with patch.object(WeChatDraftClient, "from_environment", return_value=client):
                    with patch.object(WeChatDraftClient, "resolve_thumb_media_id", side_effect=SocialPublishError("invalid ip")):
                        result = main([
                            "syndicate",
                            "--input", str(candidates),
                            "--output-dir", str(output),
                            "--cover", str(cover),
                            "--date", self.day.isoformat(),
                            "--publish-wechat",
                        ])
            self.assertEqual(result, 1)
            manifest = json.loads((output / self.day.isoformat() / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["platforms"]["wechat"]["status"], "failed")
            self.assertEqual(manifest["platforms"]["wechat"]["error"], "invalid ip")


if __name__ == "__main__":
    unittest.main()
