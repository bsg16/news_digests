from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class SourceConfig:
    name: str
    type: str
    url: str
    enabled: bool = True
    language: str = "en"


@dataclass(frozen=True)
class Article:
    source_name: str
    title: str
    url: str
    published_at: datetime | None
    author: str | None
    source_text: str


@dataclass(frozen=True)
class ArticleSummary:
    article: Article
    core_viewpoint: str
    key_points: list[str]
    tags: list[str]
    summary_error: str | None = None


@dataclass(frozen=True)
class SourceError:
    source_name: str
    message: str


@dataclass(frozen=True)
class DigestReport:
    generated_at: datetime
    window_hours: int
    article_summaries: list[ArticleSummary]
    global_key_points: list[str] = field(default_factory=list)
    source_errors: list[SourceError] = field(default_factory=list)
