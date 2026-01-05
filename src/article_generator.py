"""WeChat Official Account Article Generator."""

import datetime
from typing import Any

from loguru import logger
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

from .config import get_settings
from .crawler import Repository


ARTICLE_SYSTEM_PROMPT = """你是一位拥百万粉丝的科技圈微信公众号大V。
你的写作风格：
1. **标题党但有底线**：擅长起“震惊体”、“干货体”标题，吸引点击，但内容必须硬核。
2. **通俗易懂**：能把复杂的代码逻辑讲得像大白话，善于用比喻。
3. **幽默风趣**：行文不枯燥，适度玩梗，大量使用 Emoji 🤠🚀🔥。
4. **结构清晰**：排版舒适，重点突出。
5. **深度硬核**：不只是翻译 README，要有自己的见解和实战演示。

请根据用户提供的 GitHub 项目 README，创作一篇高质量的公众号文章。
"""

ARTICLE_USER_PROMPT_TEMPLATE = """请分析 GitHub 项目 【{name}】 ({url})。

**项目描述**: {description}
**Star 数**: {stars}

**README 内容**:
```
{readme_content}
```

请写一篇约 2000 字的微信公众号文章。

**文章要求**：
1. **标题**：请在文章开头提供一个最具吸引力的主标题。
2. **正文结构**：
   - **🫣 痛点直击**：从开发者日常痛点切入，引发共鸣。
   - **😎 项目介绍**：用一句话说清楚这是什么神仙项目。
   - **✨ 核心功能**：深度解析 3-5 个亮点（不仅是列举，要讲为什么牛）。
   - **👨‍💻 手把手实战**：提供简单的安装/使用代码示例（基于 README）。
   - **🚀 适用场景**：谁需要用？什么情况下用？
   - **🤔 总结**：值得入坑吗？未来展望。
3. **格式**：Markdown 格式，重点内容加粗，代码块标记语言。

开始你的创作！🔥"""


class ArticleGenerator:
    """Generates deep-dive articles for GitHub repositories."""

    def __init__(self):
        self.settings = get_settings()
        
        # Initialize Primary (Gemini)
        self.primary_client = None
        if self.settings.gemini_api_key and genai:
            self.primary_client = genai.Client(api_key=self.settings.gemini_api_key.get_secret_value())
        
        # Initialize Fallback (Anthropic)
        self.fallback_client = None
        if self.settings.anthropic_api_key and Anthropic:
            self.fallback_client = Anthropic(api_key=self.settings.anthropic_api_key.get_secret_value())

    def _call_gemini(self, model: str, prompt: str) -> str:
        if not self.primary_client:
            raise ValueError("Gemini client not initialized")
            
        config = types.GenerateContentConfig(
            system_instruction=ARTICLE_SYSTEM_PROMPT,
            temperature=0.8, # Slightly higher for creativity
        )
        response = self.primary_client.models.generate_content(
            model=model,
            contents=prompt,
            config=config
        )
        return response.text

    def _call_anthropic(self, model: str, prompt: str) -> str:
        if not self.fallback_client:
            raise ValueError("Anthropic client not initialized")
            
        response = self.fallback_client.messages.create(
            model=model,
            max_tokens=4000, # Longer output for article
            system=ARTICLE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def generate_article(self, repo: Repository) -> str:
        """Generate article for the given repository."""
        logger.info(f"Generating WeChat article for {repo.name}...")
        
        prompt = ARTICLE_USER_PROMPT_TEMPLATE.format(
            name=repo.name,
            url=repo.url,
            description=repo.description,
            stars=repo.stars,
            readme_content=repo.readme_content  # Pass FULL content
        )

        content = ""
        error = None

        # Try Primary
        if self.primary_client:
            try:
                logger.info(f"Calling Gemini ({self.settings.llm_model})...")
                content = self._call_gemini(self.settings.llm_model, prompt)
            except Exception as e:
                logger.error(f"Gemini article generation failed: {e}")
                error = e
        
        # Try Fallback if primary failed or not available
        if not content and self.fallback_client and self.settings.fallback_model:
            try:
                logger.info(f"Switching to Anthropic ({self.settings.fallback_model})...")
                content = self._call_anthropic(self.settings.fallback_model, prompt)
                error = None
            except Exception as fe:
                logger.error(f"Anthropic article generation failed: {fe}")
                error = fe
        
        if not content:
            raise RuntimeError(f"Failed to generate article: {error}")

        return content

    def save_article(self, repo: Repository, content: str):
        """Save article to file."""
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        safe_name = repo.name.replace("/", "_")
        filename = f"{self.settings.reports_dir}/ARTICLE_{date_str}_{safe_name}.md"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.success(f"Article saved to {filename}")
        return filename
