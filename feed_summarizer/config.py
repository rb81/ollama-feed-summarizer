"""Configuration loading and validation using Pydantic."""

from __future__ import annotations

from pathlib import Path
from typing import Union

import yaml
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    base_url: str = "http://localhost:11434/v1"
    api_key: str = "ollama"
    model: str = "llama3.2:3b"
    timeout: int = 120
    max_retries: int = 3


class FeedsConfig(BaseModel):
    file: str = "feeds.txt"
    articles_per_feed: int = 5
    fetch_timeout: int = 30
    failure_threshold: int = 3


class ConcurrencyConfig(BaseModel):
    max_feeds: int = 1
    max_summaries: int = 1


class OutputConfig(BaseModel):
    folder: str = "output"
    formats: list[str] = Field(default_factory=lambda: ["markdown"])


class AppConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    feeds: FeedsConfig = Field(default_factory=FeedsConfig)
    concurrency: ConcurrencyConfig = Field(default_factory=ConcurrencyConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)


def load_config(config_path: Union[str, Path] = "config.yaml") -> AppConfig:
    """Load and validate configuration from a YAML file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {path}\n"
            "Copy config.yaml.example to config.yaml and update it."
        )

    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    return AppConfig(**raw)
