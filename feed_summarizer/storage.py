"""SQLite-based article deduplication and history tracking."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Union


class ArticleStore:
    """Tracks summarized articles to avoid duplicates across runs."""

    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                feed_url TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS feed_failures (
                feed_url TEXT PRIMARY KEY,
                consecutive_failures INTEGER NOT NULL DEFAULT 0,
                last_failure TEXT
            )
        """)
        self._conn.commit()

    def has_article(self, url: str) -> bool:
        """Check if an article URL has already been summarized."""
        cursor = self._conn.execute(
            "SELECT 1 FROM articles WHERE url = ?", (url,)
        )
        return cursor.fetchone() is not None

    def save_article(
        self, url: str, title: str, summary: str, feed_url: str
    ) -> None:
        """Save a summarized article."""
        self._conn.execute(
            "INSERT OR IGNORE INTO articles (url, title, summary, feed_url, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (url, title, summary, feed_url, datetime.now().isoformat()),
        )
        self._conn.commit()

    def record_feed_failure(self, feed_url: str) -> int:
        """Record a feed failure and return the new consecutive failure count."""
        now = datetime.now().isoformat()
        self._conn.execute(
            """
            INSERT INTO feed_failures (feed_url, consecutive_failures, last_failure)
            VALUES (?, 1, ?)
            ON CONFLICT(feed_url) DO UPDATE SET
                consecutive_failures = consecutive_failures + 1,
                last_failure = ?
            """,
            (feed_url, now, now),
        )
        self._conn.commit()
        cursor = self._conn.execute(
            "SELECT consecutive_failures FROM feed_failures WHERE feed_url = ?",
            (feed_url,),
        )
        return cursor.fetchone()[0]

    def reset_feed_failures(self, feed_url: str) -> None:
        """Reset failure count for a feed that succeeded."""
        self._conn.execute(
            "DELETE FROM feed_failures WHERE feed_url = ?", (feed_url,)
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
