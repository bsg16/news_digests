from __future__ import annotations

from typing import Protocol

from news_digest.models import Article, ArticleSummary


class Summarizer(Protocol):
    def summarize_article(self, item: Article) -> ArticleSummary:
        raise NotImplementedError

    def summarize_global_key_points(self, summaries: list[ArticleSummary]) -> list[str]:
        raise NotImplementedError
