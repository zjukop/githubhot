import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from test_reporting import repo
from githubhot.social import (
    WeChatDraftClient,
    render_wechat_draft,
    render_x_thread,
    render_xiaohongshu_draft,
    record_delivery,
    write_social_drafts,
)


class SocialDraftTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repos = [repo(), repo(), repo()]
        self.day = date(2026, 8, 15)
        self.url = "https://github.com/zjukop/githubhot/blob/main/daily/2026/08/2026-08-15.md"

    def test_wechat_is_styled_html_with_source(self) -> None:
        draft = render_wechat_draft(self.repos, self.day, self.url)
        self.assertEqual(draft.format, "html")
        self.assertIn("TOP 1", draft.content)
        self.assertIn("适合谁", draft.content)
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
        self.assertEqual(len(posts), 1)
        self.assertTrue(all(len(post) <= 270 for post in posts))
        self.assertIn(self.url, posts[0])
        self.assertIn("\n\n", posts[0])
        self.assertTrue(all(repo_item.full_name in posts[0] for repo_item in self.repos))

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


if __name__ == "__main__":
    unittest.main()
