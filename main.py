#!/usr/bin/env python3
"""
GitHub Daily Trends AI - Main entry point.

Automatically fetches GitHub trending projects, summarizes them with AI,
and sends notifications to configured channels.
"""

import sys
from datetime import datetime, timezone

from loguru import logger

from src.ai_summarizer import summarize_repos
from src.config import get_settings
from src.crawler import crawl_trending
from src.notifier import send_notifications
from src.reporter import generate_report


def setup_logging():
    """Configure loguru logger."""
    logger.remove()  # Remove default handler

    # Console output with colors
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        level="INFO",
        colorize=True,
    )

    # File output for debugging
    logger.add(
        "logs/github_trends_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="7 days",
        level="DEBUG",
        encoding="utf-8",
    )


def main():
    """Main execution function."""
    setup_logging()

    logger.info("=" * 60)
    logger.info("GitHub Daily Trends AI - Starting")
    logger.info(f"Time: {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 60)

    settings = get_settings()

    # Step 1: Crawl trending repositories
    logger.info("Step 1/4: Crawling GitHub trending repositories...")
    try:
        crawler_result = crawl_trending()
        logger.info(
            f"Crawled {len(crawler_result.repos)} repositories from {crawler_result.source}"
        )
    except Exception as e:
        logger.error(f"Failed to crawl repositories: {e}")
        sys.exit(1)

    if not crawler_result.repos:
        logger.error("No repositories found, exiting")
        sys.exit(1)

    # Step 2: AI Summarization
    logger.info("Step 2/4: Generating AI summaries...")
    try:
        summary_result = summarize_repos(crawler_result.repos)
        logger.info(
            f"Generated {len(summary_result.all_summaries)} summaries "
            f"({len(summary_result.top_picks)} top picks)"
        )
    except Exception as e:
        logger.error(f"Failed to generate summaries: {e}")
        sys.exit(1)

    # Step 3: Generate Report
    logger.info("Step 3/4: Generating markdown report...")
    try:
        report_path = generate_report(crawler_result, summary_result)
        logger.info(f"Report saved to: {report_path}")
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        # Continue even if report fails

    # Step 4: Send Notifications
    logger.info("Step 4/4: Sending notifications...")
    try:
        notification_results = send_notifications(summary_result)
        for platform, success in notification_results.items():
            status = "✓" if success else "✗"
            logger.info(f"  {status} {platform}")
    except Exception as e:
        logger.error(f"Failed to send notifications: {e}")

    # Summary
    logger.info("=" * 60)
    logger.success("GitHub Daily Trends AI - Completed!")
    logger.info(f"Total repos: {len(crawler_result.repos)}")
    logger.info(f"Top picks: {len(summary_result.top_picks)}")
    logger.info(f"Report: {report_path if 'report_path' in dir() else 'N/A'}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
