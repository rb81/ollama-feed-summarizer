# Feed Summarizer

![Feed Summarizer](/header.png)

A fast, modern RSS feed summarizer that works with **any OpenAI-compatible LLM provider** — Ollama, OpenRouter, OpenAI, and more.

> **v2.0 — Major Overhaul:** This project was originally built as a simple, cheap, and efficient way to summarize daily news feeds using [Ollama](https://ollama.com/) running locally. It has since been completely rewritten with async feed fetching, full article extraction, SQLite deduplication, configurable concurrency, retry logic, and support for any OpenAI-compatible provider.

## Features

- **Provider-agnostic** — Works with Ollama, OpenRouter, OpenAI, or any OpenAI-compatible API
- **Full article extraction** — Fetches complete article content from the web when RSS feeds only provide snippets
- **Article deduplication** — SQLite-backed history ensures articles are never summarized twice, even across runs
- **Progress continuation** — Stop and restart anytime; already-processed articles are automatically skipped
- **Configurable concurrency** — Run sequentially for local models or in parallel for cloud APIs
- **Resilient feed handling** — Retry with exponential backoff; feeds are only removed after configurable consecutive failures
- **Beautiful CLI output** — Rich progress bars and colored status messages
- **Multiple output formats** — Markdown and/or JSON

## Requirements

- Python 3.9+
- An OpenAI-compatible LLM API (e.g., [Ollama](https://ollama.com/) running locally)

## Quick Start

1. **Clone and install:**
   ```bash
   git clone https://github.com/rb81/ollama-feed-summarizer.git
   cd ollama-feed-summarizer
   pip install -e .
   ```

2. **Configure:**
   ```bash
   cp config.yaml.example config.yaml
   cp feeds.txt.example feeds.txt
   ```
   Edit `config.yaml` with your LLM provider details and add your RSS feeds to `feeds.txt`.

3. **Run:**
   ```bash
   python -m feed_summarizer
   ```
   Or use the installed command:
   ```bash
   feed-summarizer
   ```

## Configuration

All settings are in `config.yaml`:

```yaml
# LLM Provider (any OpenAI-compatible API)
llm:
  base_url: http://localhost:11434/v1   # Ollama
  api_key: ollama
  model: llama3.2:3b
  timeout: 120
  max_retries: 3

# Feed settings
feeds:
  file: feeds.txt
  articles_per_feed: 5
  fetch_timeout: 30
  failure_threshold: 3  # Remove feed after N consecutive failures

# Concurrency (set to 1 for local models on limited hardware)
concurrency:
  max_feeds: 1       # Parallel feed fetches
  max_summaries: 1   # Parallel LLM calls

# Output
output:
  folder: output
  formats:
    - markdown
    # - json
```

### Provider Examples

**Ollama (local):**
```yaml
llm:
  base_url: http://localhost:11434/v1
  api_key: ollama
  model: llama3.2:3b
```

**OpenRouter:**
```yaml
llm:
  base_url: https://openrouter.ai/api/v1
  api_key: sk-or-v1-your-key-here
  model: meta-llama/llama-3.1-8b-instruct
```

**OpenAI:**
```yaml
llm:
  base_url: https://api.openai.com/v1
  api_key: sk-your-key-here
  model: gpt-4o-mini
```

## How It Works

1. **Reads** RSS feed URLs from `feeds.txt`
2. **Fetches** feeds concurrently (with configurable parallelism and retry with backoff)
3. **Extracts** full article content — if an RSS entry only has a snippet, the tool fetches the full web page and extracts text from `<article>` or `<main>` tags
4. **Deduplicates** — checks each article against a local SQLite database and skips any that were already summarized in previous runs
5. **Summarizes** new articles using your configured LLM with a prompt optimized for insightful, multi-sentence analysis
6. **Writes** output files (Markdown and/or JSON)

### Deduplication & Progress Continuation

The tool maintains a `history.db` SQLite database in the output folder. This means:

- **No duplicate work** — Articles are tracked by URL. If you run the tool multiple times a day, it only summarizes new articles.
- **Resumable** — If the tool is interrupted mid-run (Ctrl+C, crash, timeout), already-completed articles are saved. The next run picks up where it left off.
- **Incremental** — Add new feeds to `feeds.txt` at any time. Only their new articles will be processed.

### Feed Failure Handling

Feeds that fail to fetch are not immediately removed. The tool tracks consecutive failures per feed:

- First failure: logged as a warning, feed stays active
- After N consecutive failures (configurable via `failure_threshold`): feed is removed from `feeds.txt`
- A successful fetch resets the failure counter

This prevents temporary network issues from permanently removing a feed.

## Output

All output is saved to the `output/` folder (gitignored by default):

- `YYYY-MM-DD_feed-summaries.md` — Markdown summary with article titles, summaries, and links
- `YYYY-MM-DD_feed-summaries.json` — Structured JSON output (if enabled)
- `history.db` — SQLite database for deduplication and history

### Example Output

```markdown
# News for Monday, June 15, 2026

## The FBI built a small town to simulate cyberattacks

The FBI opened a 22,000-square-foot Cyber Range in Huntsville, Alabama that
replicates an entire town—including a convenience store, gas station, hospital
and fully furnished homes—complete with a realistic data center and power
infrastructure. The facility lets investigators simulate real-world cyber-attacks
on critical services, giving agents hands-on training to defend against
sophisticated intrusions.

[Read more](https://www.theverge.com/tech/949648/fbi-fake-town-cyberattacks)

---
```

## Project Structure

```
feed_summarizer/
├── __init__.py        # Package metadata
├── __main__.py        # Entry point
├── config.py          # Pydantic config validation + YAML loading
├── feeds.py           # Async feed fetching, full article extraction, HTML→text
├── llm.py             # OpenAI-compatible LLM client with retry
├── output.py          # Markdown and JSON output generation
├── storage.py         # SQLite deduplication and feed failure tracking
└── summarizer.py      # Main orchestrator
```

## License

MIT — see [LICENSE](LICENSE) for details.
