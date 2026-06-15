"""OpenAI-compatible LLM client for article summarization."""

from __future__ import annotations

from typing import Optional

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import LLMConfig

SYSTEM_PROMPT = (
    "You are an expert news analyst who writes concise, insightful summaries. "
    "Your summaries capture the key facts, why they matter, and any broader implications. "
    "You write in clear, direct prose — no filler, no hedging."
)

USER_PROMPT_TEMPLATE = """Summarize the following article in 2-4 sentences. Include:
- The core news or finding
- Why it matters or who it affects
- Any notable context or implications

Article title: {title}

Article content:
{content}

Write ONLY the summary — no preamble, no labels, no bullet points."""


def create_client(config: LLMConfig) -> OpenAI:
    """Create an OpenAI-compatible client."""
    return OpenAI(
        base_url=config.base_url,
        api_key=config.api_key,
        timeout=config.timeout,
        max_retries=config.max_retries,
    )


def summarize_text(client: OpenAI, model: str, content: str, title: str = "") -> Optional[str]:
    """Summarize article content using the LLM.

    Returns the summary string, or None on failure.
    """

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        reraise=True,
    )
    def _call() -> str:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT_TEMPLATE.format(
                    title=title, content=content
                )},
            ],
        )
        return response.choices[0].message.content.strip()

    try:
        return _call()
    except Exception:
        return None
