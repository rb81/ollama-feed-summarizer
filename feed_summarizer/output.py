"""Output generation (Markdown and JSON)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Union


@dataclass
class SummaryEntry:
    title: str
    summary: str
    link: str
    feed_url: str


def generate_markdown(entries: list[SummaryEntry], date: datetime) -> str:
    """Generate a formatted Markdown document from summary entries."""
    formatted_date = date.strftime("%A, %B %d, %Y")
    lines = [f"# News for {formatted_date}\n"]

    for entry in entries:
        lines.append(f"## {entry.title}\n")
        lines.append(f"{entry.summary}\n")
        if entry.link:
            lines.append(f"[Read more]({entry.link})\n")
        lines.append("---\n")

    return "\n".join(lines)


def generate_json(entries: list[SummaryEntry], date: datetime) -> str:
    """Generate a JSON document from summary entries."""
    data = {
        "date": date.isoformat(),
        "articles": [
            {
                "title": e.title,
                "summary": e.summary,
                "link": e.link,
                "feed_url": e.feed_url,
            }
            for e in entries
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def write_outputs(
    entries: list[SummaryEntry],
    output_folder: Union[str, Path],
    formats: list[str],
) -> list[Path]:
    """Write output files and return the list of created file paths."""
    folder = Path(output_folder)
    folder.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    created: list[Path] = []

    if "markdown" in formats:
        md_path = folder / f"{date_str}_feed-summaries.md"
        md_path.write_text(generate_markdown(entries, now))
        created.append(md_path)

    if "json" in formats:
        json_path = folder / f"{date_str}_feed-summaries.json"
        json_path.write_text(generate_json(entries, now))
        created.append(json_path)

    return created
