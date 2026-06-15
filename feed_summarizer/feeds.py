"""Async RSS feed fetching and parsing with full article extraction."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Optional

import aiohttp
import feedparser
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import FeedsConfig


# Minimum content length (chars) before we attempt to fetch the full article
_MIN_CONTENT_LENGTH = 500


@dataclass
class Article:
    title: str
    link: str
    content: str
    feed_url: str


class _HTMLTextExtractor(HTMLParser):
    """Simple HTML to plain text converter."""

    def __init__(self):
        super().__init__()
        self._result: list[str] = []
        self._skip = False
        self._skip_tags = {"script", "style", "nav", "header", "footer", "aside"}

    def handle_starttag(self, tag, attrs):
        if tag in self._skip_tags:
            self._skip = True
        if tag in ("p", "br", "div", "h1", "h2", "h3", "h4", "li"):
            self._result.append("\n")

    def handle_endtag(self, tag):
        if tag in self._skip_tags:
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self._result.append(data)

    def get_text(self) -> str:
        text = "".join(self._result)
        # Collapse multiple whitespace/newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()


def _html_to_text(html: str) -> str:
    """Convert HTML to clean plain text."""
    extractor = _HTMLTextExtractor()
    extractor.feed(html)
    return extractor.get_text()


def read_feed_urls(file_path: str) -> list[str]:
    """Read feed URLs from a text file (one per line)."""
    from pathlib import Path

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Feeds file not found: {file_path}")

    urls = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    if not urls:
        raise ValueError(f"No feeds found in {file_path}")
    return urls


def write_feed_urls(file_path: str, urls: list[str]) -> None:
    """Write feed URLs to a text file."""
    from pathlib import Path

    Path(file_path).write_text("\n".join(urls) + "\n" if urls else "")


def _extract_feed_content(entry) -> str:
    """Extract the best available content from a feed entry."""
    # Prefer full content field, then summary, then description
    candidates = []

    # content:encoded or content field (often full article in RSS 2.0)
    content_list = entry.get("content", [])
    if content_list:
        for c in content_list:
            val = c.get("value", "")
            if val:
                candidates.append(val)

    # summary (sometimes full article, sometimes snippet)
    summary = entry.get("summary", "")
    if summary:
        candidates.append(summary)

    # description
    desc = entry.get("description", "")
    if desc and desc != summary:
        candidates.append(desc)

    # Return the longest content available from the feed
    if candidates:
        best = max(candidates, key=len)
        return _html_to_text(best)

    return entry.get("title", "")


async def _fetch_full_article(
    session: aiohttp.ClientSession,
    url: str,
    timeout: int,
) -> Optional[str]:
    """Fetch the full article page and extract its text content."""
    if not url:
        return None

    try:
        t = aiohttp.ClientTimeout(total=timeout)
        async with session.get(url, timeout=t, allow_redirects=True) as resp:
            if resp.status != 200:
                return None
            html = await resp.text()
    except Exception:
        return None

    # Try to find <article> tag content first (most news sites use this)
    article_match = re.search(
        r"<article[^>]*>(.*?)</article>", html, re.DOTALL | re.IGNORECASE
    )
    if article_match:
        return _html_to_text(article_match.group(1))

    # Fallback: look for main content area
    main_match = re.search(
        r'<main[^>]*>(.*?)</main>', html, re.DOTALL | re.IGNORECASE
    )
    if main_match:
        return _html_to_text(main_match.group(1))

    # Last resort: extract from body but this is noisy
    body_match = re.search(
        r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE
    )
    if body_match:
        text = _html_to_text(body_match.group(1))
        # Only use if we got substantial text
        if len(text) > 500:
            return text

    return None


async def _fetch_single_feed(
    session: aiohttp.ClientSession,
    url: str,
    articles_per_feed: int,
    fetch_timeout: int,
) -> Optional[list[Article]]:
    """Fetch and parse a single RSS feed, enriching with full article content."""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _do_fetch() -> bytes:
        timeout = aiohttp.ClientTimeout(total=fetch_timeout)
        async with session.get(url, timeout=timeout) as resp:
            resp.raise_for_status()
            return await resp.read()

    try:
        data = await _do_fetch()
    except Exception:
        return None

    feed = feedparser.parse(data)
    if feed.get("bozo", 0) == 1:
        return None

    articles: list[Article] = []
    for entry in feed.entries[:articles_per_feed]:
        content = _extract_feed_content(entry)
        link = entry.get("link", "")

        # If the RSS content is too short, fetch the full article
        if len(content) < _MIN_CONTENT_LENGTH and link:
            full_text = await _fetch_full_article(session, link, fetch_timeout)
            if full_text and len(full_text) > len(content):
                content = full_text

        if content:
            # Truncate extremely long articles to avoid token limits
            if len(content) > 12000:
                content = content[:12000] + "\n\n[Content truncated...]"

            articles.append(
                Article(
                    title=entry.get("title", "Untitled"),
                    link=link,
                    content=content,
                    feed_url=url,
                )
            )

    return articles if articles else None


async def fetch_all_feeds(
    urls: list[str],
    config: FeedsConfig,
    max_concurrent: int = 1,
) -> dict[str, Optional[list[Article]]]:
    """Fetch all feeds with controlled concurrency.

    Returns a dict mapping feed URL -> list of articles (or None on failure).
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    results: dict[str, Optional[list[Article]]] = {}

    async def _bounded_fetch(feed_url: str) -> None:
        async with semaphore:
            result = await _fetch_single_feed(
                session,
                feed_url,
                config.articles_per_feed,
                config.fetch_timeout,
            )
            results[feed_url] = result

    async with aiohttp.ClientSession() as session:
        tasks = [_bounded_fetch(url) for url in urls]
        await asyncio.gather(*tasks)

    return results
