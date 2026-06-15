"""Entry point: python -m feed_summarizer"""

import asyncio
import sys

from rich.console import Console

from .config import load_config
from .summarizer import run

console = Console()


def main() -> None:
    try:
        config = load_config()
    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Configuration error:[/bold red] {e}")
        sys.exit(1)

    try:
        asyncio.run(run(config))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user.[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    main()
