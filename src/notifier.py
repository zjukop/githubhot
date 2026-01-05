"""Notification module supporting multiple webhook platforms."""

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_fixed

from .ai_summarizer import ProjectSummary, SummaryResult
from .config import get_settings


class BaseNotifier(ABC):
    """Abstract base class for notification handlers."""

    @abstractmethod
    def send(self, summaries: list[ProjectSummary]) -> bool:
        """Send notification with project summaries."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Platform name for logging."""
        pass


class FeishuNotifier(BaseNotifier):
    """Feishu (飞书) webhook notifier."""

    name = "Feishu"

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def _build_card(self, summaries: list[ProjectSummary]) -> dict:
        """Build Feishu interactive card message."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"🔥 **GitHub 今日精选** | {today}\n找到 {len(summaries)} 个热门项目",
                },
            },
            {"tag": "hr"},
        ]

        for s in summaries[:5]:  # Limit to 5 for readability
            stars = "⭐" * s.score
            elements.append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            f"**[{s.repo.name}]({s.repo.url})**\n"
                            f"{s.one_liner_cn}\n"
                            f"{stars} | {s.repo.language} | ⭐{s.repo.stars:,}"
                        ),
                    },
                }
            )
            elements.append({"tag": "hr"})

        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": "🚀 GitHub Daily Trends"},
                    "template": "blue",
                },
                "elements": elements,
            },
        }

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def send(self, summaries: list[ProjectSummary]) -> bool:
        payload = self._build_card(summaries)
        resp = httpx.post(self.webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info(f"Feishu notification sent successfully")
        return True


class DingTalkNotifier(BaseNotifier):
    """DingTalk (钉钉) webhook notifier."""

    name = "DingTalk"

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def _build_message(self, summaries: list[ProjectSummary]) -> dict:
        """Build DingTalk markdown message."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        lines = [f"## 🔥 GitHub 今日精选 ({today})\n"]

        for s in summaries[:5]:
            stars = "⭐" * s.score
            lines.append(f"### [{s.repo.name}]({s.repo.url})")
            lines.append(f"> {s.one_liner_cn}")
            lines.append(f"")
            lines.append(f"- 语言: {s.repo.language} | Stars: {s.repo.stars:,}")
            lines.append(f"- 推荐: {stars}")
            lines.append(f"- 适用: {s.use_case}")
            lines.append("")

        return {
            "msgtype": "markdown",
            "markdown": {"title": "GitHub Daily Trends", "text": "\n".join(lines)},
        }

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def send(self, summaries: list[ProjectSummary]) -> bool:
        payload = self._build_message(summaries)
        resp = httpx.post(self.webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info(f"DingTalk notification sent successfully")
        return True


class SlackNotifier(BaseNotifier):
    """Slack webhook notifier."""

    name = "Slack"

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def _build_blocks(self, summaries: list[ProjectSummary]) -> dict:
        """Build Slack blocks message."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"🔥 GitHub Daily Trends - {today}"},
            },
            {"type": "divider"},
        ]

        for s in summaries[:5]:
            stars = "⭐" * s.score
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*<{s.repo.url}|{s.repo.name}>*\n"
                            f"{s.one_liner_cn}\n"
                            f"{stars} | {s.repo.language} | ⭐ {s.repo.stars:,}"
                        ),
                    },
                }
            )

        return {"blocks": blocks}

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def send(self, summaries: list[ProjectSummary]) -> bool:
        payload = self._build_blocks(summaries)
        resp = httpx.post(self.webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info(f"Slack notification sent successfully")
        return True


class TelegramNotifier(BaseNotifier):
    """Telegram bot notifier."""

    name = "Telegram"

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    def _build_message(self, summaries: list[ProjectSummary]) -> str:
        """Build Telegram HTML message."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        lines = [f"<b>🔥 GitHub Daily Trends - {today}</b>\n"]

        for s in summaries[:5]:
            stars = "⭐" * s.score
            lines.append(f'<b><a href="{s.repo.url}">{s.repo.name}</a></b>')
            lines.append(f"<i>{s.one_liner_cn}</i>")
            lines.append(f"{stars} | {s.repo.language} | ⭐ {s.repo.stars:,}")
            lines.append("")

        return "\n".join(lines)

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def send(self, summaries: list[ProjectSummary]) -> bool:
        payload = {
            "chat_id": self.chat_id,
            "text": self._build_message(summaries),
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        resp = httpx.post(self.api_url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info(f"Telegram notification sent successfully")
        return True


class NotificationManager:
    """Manage and dispatch notifications to configured platforms."""

    def __init__(self):
        self.settings = get_settings()
        self.notifiers: list[BaseNotifier] = []
        self._init_notifiers()

    def _init_notifiers(self):
        """Initialize enabled notifiers based on configuration."""
        if self.settings.feishu_webhook_url:
            self.notifiers.append(FeishuNotifier(self.settings.feishu_webhook_url))
            logger.info("Feishu notifier enabled")

        if self.settings.dingtalk_webhook_url:
            self.notifiers.append(DingTalkNotifier(self.settings.dingtalk_webhook_url))
            logger.info("DingTalk notifier enabled")

        if self.settings.slack_webhook_url:
            self.notifiers.append(SlackNotifier(self.settings.slack_webhook_url))
            logger.info("Slack notifier enabled")

        if self.settings.telegram_bot_token and self.settings.telegram_chat_id:
            self.notifiers.append(
                TelegramNotifier(
                    self.settings.telegram_bot_token,
                    self.settings.telegram_chat_id,
                )
            )
            logger.info("Telegram notifier enabled")

        if not self.notifiers:
            logger.warning("No notification channels configured")

    def notify(self, result: SummaryResult) -> dict[str, bool]:
        """
        Send notifications to all configured platforms.

        Returns:
            Dict mapping platform name to success status.
        """
        if not self.notifiers:
            logger.info("No notifiers configured, skipping notifications")
            return {}

        # Only send top picks to notifications (to avoid spam)
        summaries = result.top_picks if result.top_picks else result.quick_looks[:3]

        if not summaries:
            logger.warning("No summaries to notify")
            return {}

        results = {}
        for notifier in self.notifiers:
            try:
                results[notifier.name] = notifier.send(summaries)
            except Exception as e:
                logger.error(f"Failed to send {notifier.name} notification: {e}")
                results[notifier.name] = False

        return results


def send_notifications(result: SummaryResult) -> dict[str, bool]:
    """Convenience function to send notifications."""
    manager = NotificationManager()
    return manager.notify(result)
