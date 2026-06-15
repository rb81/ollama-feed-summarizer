"""Main orchestrator: coordinates feed fetching, summarization, and output."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from openai import OpenAI
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from .config import AppConfig
from .feeds import Article, fetch_all_feeds
from .llm import summarize_text
from .output import SummaryEntry, write_outputs
from .storage import ArticleStore

console = Console()


def _summarize_articles(
    articles: list[Article],
    client: OpenAI,
    model: str,
    store: ArticleStore,
    max_concurrent: int,
) -> list[SummaryEntry]:
    """Summarize articles with controlled concurrency using threads.

    Uses threads because the OpenAI SDK is synchronous.
    """
    entries: list[SummaryEntry] = []
    to_summarize: list[Article] = []

    # Filter out already-seen articles
    for article in articles:
        if article.link and store.has_article(article.link):
            console.print(f"  [dim]Skipping (already summarized): {article.title}[/dim]")
        else:
            to_summarize.append(article)

    if not to_summarize:
        return entries

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Summarizing articles...", total=len(to_summarize))

        def _process(article: Article) -> Optional[SummaryEntry]:
            summary = summarize_text(client, model, article.content, title=article.title)
            progress.advance(task)
            if summary:
                store.save_article(article.link, article.title, summary, article.feed_url)
                return SummaryEntry(
                    title=article.title,
                    summary=summary,
                    link=article.link,
                    feed_url=article.feed_url,
                )
            return None

        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = [executor.submit(_process, a) for a in to_summarize]
            for future in futures:
                result = future.result()
                if result:
                    entries.append(result)

    return entries


async def run(config: AppConfig) -> None:
    """Main entry point for the summarizer pipeline."""
    from pathlib import Path
    from .feeds import read_feed_urls, write_feed_urls
    from .llm import create_client

    console.print("\n[bold blue]Feed Summarizer v2.0[/bold blue]\n")

    # Setup
    output_folder = Path(config.output.folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    store = ArticleStore(output_folder / "history.db")
    client = create_client(config.llm)

    # Read feeds
    try:
        feed_urls = read_feed_urls(config.feeds.file)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return

    console.print(f"[green]Loaded {len(feed_urls)} feed(s)[/green]")

    # Fetch feeds
    console.print("\n[bold]Fetching feeds...[/bold]")
    feed_results = await fetch_all_feeds(
        feed_urls, config.feeds, max_concurrent=config.concurrency.max_feeds
    )

    # Process results
    all_articles: list[Article] = []
    feeds_to_remove: list[str] = []

    for url, articles in feed_results.items():
        if articles:
            store.reset_feed_failures(url)
            console.print(f"  [green]✓[/green] {url} ({len(articles)} articles)")
            all_articles.extend(articles)
        else:
            failures = store.record_feed_failure(url)
            if failures >= config.feeds.failure_threshold:
                console.print(
                    f"  [red]✗[/red] {url} (failed {failures}x — removing)"
                )
                feeds_to_remove.append(url)
            else:
                console.print(
                    f"  [yellow]![/yellow] {url} (failed {failures}/{config.feeds.failure_threshold})"
                )

    # Update feeds file if any removed
    if feeds_to_remove:
        remaining = [u for u in feed_urls if u not in feeds_to_remove]
        write_feed_urls(config.feeds.file, remaining)
        console.print(
            f"\n[yellow]Removed {len(feeds_to_remove)} feed(s) after repeated failures[/yellow]"
        )

    if not all_articles:
        console.print("\n[yellow]No articles to summarize.[/yellow]")
        store.close()
        return

    console.print(f"\n[bold]Summarizing {len(all_articles)} article(s)...[/bold]\n")

    # Summarize
    entries = _summarize_articles(
        all_articles,
        client,
        config.llm.model,
        store,
        max_concurrent=config.concurrency.max_summaries,
    )

    store.close()

    if not entries:
        console.print("[yellow]No new summaries generated.[/yellow]")
        return

    # Write output
    created_files = write_outputs(entries, config.output.folder, config.output.formats)

    console.print(f"\n[bold green]Done![/bold green] {len(entries)} article(s) summarized.")
    for f in created_files:
        console.print(f"  [blue]→[/blue] {f}")
    console.print()
