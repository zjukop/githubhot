from __future__ import annotations

import html
import json
import os
import shutil
import uuid
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from githubhot.models import Repository


class SocialPublishError(RuntimeError):
    pass


@dataclass(slots=True)
class PlatformDraft:
    platform: str
    title: str
    content: str
    source_url: str
    format: str


def _analysis(repo: Repository) -> dict[str, Any]:
    value = repo.analysis or {}
    return {
        "positioning": value.get("positioning") or repo.description or repo.full_name,
        "target_users": value.get("target_users") or ["关注开源工具的开发者。"],
        "core_capabilities": value.get("core_capabilities") or [repo.readme_summary or repo.description or "请查看官方仓库。"],
        "why_it_matters": value.get("why_it_matters") or ["项目近期获得较多社区关注。"],
        "limitations": value.get("limitations") or ["采用前请核对官方文档、许可证和安全边界。"],
        "opportunities": value.get("opportunities") or ["继续观察真实用户反馈后再判断开发机会。"],
    }


def _truncate(text: str, limit: int) -> str:
    cleaned = " ".join(text.split())
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 1].rstrip() + "…"


def _truncate_post(text: str, limit: int = 270) -> str:
    cleaned = "\n".join(line.strip() for line in text.splitlines()).strip()
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 1].rstrip() + "…"


def render_wechat_draft(repos: list[Repository], publish_date: date, source_url: str) -> PlatformDraft:
    featured = repos[:3]
    title = f"木匠逛 GitHub｜{publish_date:%m月%d日}值得拆看的 3 个项目"
    sections = []
    for rank, repo in enumerate(featured, 1):
        analysis = _analysis(repo)
        sections.append(
            f'<section style="margin:24px 0;padding:18px;border:1px solid #e5e7eb;border-radius:12px;">'
            f'<p style="margin:0 0 8px;color:#7c3aed;font-size:14px;font-weight:700;">TOP {rank}</p>'
            f'<h2 style="margin:0 0 12px;font-size:21px;line-height:1.4;">{html.escape(repo.full_name)}</h2>'
            f'<p style="color:#374151;line-height:1.8;">{html.escape(analysis["positioning"])}</p>'
            f'<p style="line-height:1.8;"><strong>适合谁：</strong>{html.escape(analysis["target_users"][0])}</p>'
            f'<p style="line-height:1.8;"><strong>核心价值：</strong>{html.escape(analysis["core_capabilities"][0])}</p>'
            f'<p style="line-height:1.8;"><strong>为什么值得看：</strong>{html.escape(analysis["why_it_matters"][0])}</p>'
            f'<p style="line-height:1.8;"><strong>采用提醒：</strong>{html.escape(analysis["limitations"][0])}</p>'
            f'<p style="line-height:1.8;"><strong>还能做什么：</strong>{html.escape(analysis["opportunities"][0])}</p>'
            f'<p style="color:#6b7280;font-size:13px;">Stars {repo.stars:,} · {html.escape(repo.language or "Unknown")} · {html.escape(repo.license or "Unknown")}</p>'
            f'<p><a href="{html.escape(repo.html_url)}" style="color:#2563eb;">打开官方仓库 →</a></p>'
            f'</section>'
        )
    content = (
        '<section style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;color:#111827;">'
        '<p style="margin:0 0 8px;color:#0891b2;font-size:14px;font-weight:700;">赛博木匠 · 今日工作台</p>'
        f'<p style="font-size:16px;line-height:1.9;">今天从 GitHub 热点里挑出 3 块值得拆看的“木料”。'
        '不只看 Stars，也看它解决什么问题、谁会真正使用、有哪些风险，以及还能延伸出什么产品机会。</p>'
        + "".join(sections)
        + f'<p style="margin-top:28px;line-height:1.8;"><a href="{html.escape(source_url)}" style="color:#2563eb;">阅读完整 GitHubHot 日报 →</a></p>'
        + '<blockquote style="margin:20px 0;padding:12px 16px;background:#f8fafc;color:#64748b;">AI 当工具，代码做木料。热度只是发现信号，不代表质量、安全性或投资价值。</blockquote>'
        + '</section>'
    )
    return PlatformDraft("wechat", title, content, source_url, "html")


def render_xiaohongshu_draft(repos: list[Repository], publish_date: date, source_url: str) -> PlatformDraft:
    featured = repos[:3]
    title = _truncate(f"GitHub热榜｜今天这3个项目值得看", 20)
    lines = [
        f"🪚 {publish_date:%m月%d日}｜木匠逛 GitHub",
        "",
        "赛博木匠今天挑了 3 个项目拆开看看：它解决什么问题、谁会真正用、有什么坑，以及还能做成什么。",
        "",
    ]
    for rank, repo in enumerate(featured, 1):
        analysis = _analysis(repo)
        lines.extend(
            [
                f"{rank}️⃣ {repo.full_name}",
                f"一句话：{_truncate(analysis['positioning'], 105)}",
                f"适合：{_truncate(analysis['target_users'][0], 70)}",
                f"亮点：{_truncate(analysis['core_capabilities'][0], 85)}",
                f"注意：{_truncate(analysis['limitations'][0], 75)}",
                f"数据：⭐ {repo.stars:,}｜{repo.language or 'Unknown'}｜{repo.license or 'Unknown'}",
                "",
            ]
        )
    lines.extend(
        [
            "💡 独立开发者视角",
            _truncate(_analysis(featured[0])["opportunities"][0], 110) if featured else "今天继续观察，不为追热点硬造项目。",
            "",
            "完整拆解已经放到 GitHubHot，主页链接查看。",
            "",
            "#GitHub #开源项目 #独立开发 #程序员 #AI工具 #赛博木匠",
        ]
    )
    content = "\n".join(lines)
    if len(content) > 900:
        tags = "#GitHub #开源项目 #独立开发 #程序员 #AI工具 #赛博木匠"
        content = f"{content[: 900 - len(tags) - 3].rstrip()}…\n\n{tags}"
    return PlatformDraft("xiaohongshu", title, content, source_url, "markdown")


def render_x_thread(repos: list[Repository], publish_date: date, source_url: str) -> PlatformDraft:
    featured = repos[:3]
    names = "\n".join(f"{rank}. {repo.full_name}" for rank, repo in enumerate(featured, 1))
    content = _truncate_post(
        f"赛博木匠 · {publish_date.isoformat()}\n\n"
        f"今天值得拆看的 3 个 GitHub 项目：\n{names}\n\n"
        f"完整中文分析：{source_url}\n"
        "#GitHub #OpenSource"
    )
    return PlatformDraft("x", f"GitHubHot {publish_date.isoformat()}", content, source_url, "post")


def write_social_drafts(
    root: Path,
    repos: list[Repository],
    publish_date: date,
    source_url: str,
    cover_path: Path | None = None,
) -> dict[str, Path]:
    output = root / publish_date.isoformat()
    output.mkdir(parents=True, exist_ok=True)
    drafts = [
        render_wechat_draft(repos, publish_date, source_url),
        render_xiaohongshu_draft(repos, publish_date, source_url),
        render_x_thread(repos, publish_date, source_url),
    ]
    paths: dict[str, Path] = {}
    for draft in drafts:
        extension = "html" if draft.format == "html" else "md"
        path = output / f"{draft.platform}.{extension}"
        path.write_text(draft.content + "\n", encoding="utf-8")
        paths[draft.platform] = path
        (output / f"{draft.platform}.json").write_text(
            json.dumps(asdict(draft), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    cover_output: Path | None = None
    if cover_path is not None:
        if not cover_path.is_file():
            raise SocialPublishError(f"social cover image does not exist: {cover_path}")
        cover_output = output / f"cover{cover_path.suffix.lower()}"
        shutil.copy2(cover_path, cover_output)
        paths["cover"] = cover_output
    manifest = {
        "date": publish_date.isoformat(),
        "source_url": source_url,
        "cover": str(cover_output) if cover_output else None,
        "platforms": {
            "wechat": {"status": "generated", "delivery": "official_api_when_configured"},
            "xiaohongshu": {"status": "generated", "delivery": "browser_required"},
            "x": {"status": "generated", "delivery": "browser_required_for_organic_draft"},
        },
    }
    manifest_path = output / "manifest.json"
    if manifest_path.is_file():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        for platform, state in previous.get("platforms", {}).items():
            if platform in manifest["platforms"] and state.get("status") == "drafted":
                manifest["platforms"][platform].update(state)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paths["manifest"] = manifest_path
    return paths


def record_delivery(manifest_path: Path, platform: str, status: str, **details: Any) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if platform not in manifest["platforms"]:
        raise SocialPublishError(f"unknown platform in manifest: {platform}")
    manifest["platforms"][platform].update({"status": status, **details})
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@dataclass(slots=True)
class WeChatDraftClient:
    app_id: str
    app_secret: str
    timeout: int = 30

    @classmethod
    def from_environment(cls) -> "WeChatDraftClient":
        values = {name: os.environ.get(name, "").strip() for name in ("WECHAT_APP_ID", "WECHAT_APP_SECRET")}
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise SocialPublishError(f"missing WeChat configuration: {', '.join(missing)}")
        return cls(values["WECHAT_APP_ID"], values["WECHAT_APP_SECRET"])

    def _request_json(self, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST" if data else "GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.load(response)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            raise SocialPublishError(f"WeChat request failed: {exc}") from exc
        if result.get("errcode") not in (None, 0):
            raise SocialPublishError(f"WeChat API error {result.get('errcode')}: {result.get('errmsg', 'unknown')}")
        return result

    def access_token(self) -> str:
        query = urllib.parse.urlencode({"grant_type": "client_credential", "appid": self.app_id, "secret": self.app_secret})
        result = self._request_json(f"https://api.weixin.qq.com/cgi-bin/token?{query}")
        token = result.get("access_token")
        if not token:
            raise SocialPublishError("WeChat response did not include access_token")
        return str(token)

    def upload_permanent_image(self, image_path: Path) -> str:
        if not image_path.is_file():
            raise SocialPublishError(f"WeChat cover image does not exist: {image_path}")
        token = self.access_token()
        boundary = f"githubhot-{uuid.uuid4().hex}"
        mime_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="media"; filename="{image_path.name}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode("utf-8") + image_path.read_bytes() + f"\r\n--{boundary}--\r\n".encode("ascii")
        query = urllib.parse.urlencode({"access_token": token, "type": "image"})
        request = urllib.request.Request(
            f"https://api.weixin.qq.com/cgi-bin/material/add_material?{query}",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.load(response)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            raise SocialPublishError(f"WeChat image upload failed: {exc}") from exc
        if result.get("errcode") not in (None, 0):
            raise SocialPublishError(f"WeChat API error {result.get('errcode')}: {result.get('errmsg', 'unknown')}")
        media_id = result.get("media_id")
        if not media_id:
            raise SocialPublishError("WeChat permanent image response did not include media_id")
        return str(media_id)

    def resolve_thumb_media_id(self, image_path: Path, cache_path: Path) -> str:
        configured = os.environ.get("WECHAT_THUMB_MEDIA_ID", "").strip()
        if configured:
            return configured
        if cache_path.is_file():
            cached = cache_path.read_text(encoding="utf-8").strip()
            if cached:
                return cached
        media_id = self.upload_permanent_image(image_path)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(media_id + "\n", encoding="utf-8")
        return media_id

    def add_draft(self, draft: PlatformDraft, thumb_media_id: str, author: str = "赛博木匠") -> str:
        token = self.access_token()
        payload = {
            "articles": [
                {
                    "title": draft.title,
                    "author": author,
                    "digest": "每天精选 GitHub 热门项目，提供中文价值分析、采用风险与独立开发机会。",
                    "content": draft.content,
                    "content_source_url": draft.source_url,
                    "thumb_media_id": thumb_media_id,
                    "need_open_comment": 0,
                    "only_fans_can_comment": 0,
                }
            ]
        }
        result = self._request_json(f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={urllib.parse.quote(token)}", payload)
        media_id = result.get("media_id")
        if not media_id:
            raise SocialPublishError("WeChat draft response did not include media_id")
        return str(media_id)
