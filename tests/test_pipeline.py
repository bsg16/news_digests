from datetime import datetime, timedelta, timezone

from news_digest.models import Article, ArticleSummary, SourceConfig
from news_digest.pipeline import (
    collect_recent_articles,
    deduplicate_articles,
    filter_articles_by_window,
    summarize_articles,
)


def article(title: str, url: str, published_at: datetime | None) -> Article:
    return Article(
        source_name="Example",
        title=title,
        url=url,
        published_at=published_at,
        author=None,
        source_text=f"{title} body",
    )


class FakeSummarizer:
    def summarize_article(self, item: Article) -> ArticleSummary:
        return ArticleSummary(
            article=item,
            core_viewpoint=f"{item.title} core",
            key_points=[f"{item.title} point"],
            tags=["测试"],
        )

    def summarize_global_key_points(self, summaries: list[ArticleSummary]) -> list[str]:
        return [f"共处理 {len(summaries)} 篇文章"]


def test_filter_articles_by_window_keeps_recent_and_unknown_dates() -> None:
    now = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
    recent = article("Recent", "https://example.com/recent", now - timedelta(hours=2))
    old = article("Old", "https://example.com/old", now - timedelta(hours=25))
    unknown = article("Unknown", "https://example.com/unknown", None)

    result = filter_articles_by_window([recent, old, unknown], now=now, window_hours=24)

    assert result == [recent, unknown]


def test_deduplicate_articles_prefers_first_url_match() -> None:
    now = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
    first = article("First", "https://example.com/item?utm_source=rss", now)
    duplicate = article("Duplicate", "https://example.com/item", now)
    second = article("Second", "https://example.com/second", now)

    result = deduplicate_articles([first, duplicate, second])

    assert result == [first, second]


def test_collect_recent_articles_continues_after_source_error() -> None:
    now = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
    good = SourceConfig(name="Good", type="rss", url="https://example.com/good.xml")
    bad = SourceConfig(name="Bad", type="rss", url="https://example.com/bad.xml")

    def fetcher(source: SourceConfig) -> list[Article]:
        if source.name == "Bad":
            raise RuntimeError("network down")
        return [article("Good story", "https://example.com/good-story", now)]

    articles, errors = collect_recent_articles([bad, good], now=now, window_hours=24, fetcher=fetcher)

    assert [item.title for item in articles] == ["Good story"]
    assert len(errors) == 1
    assert errors[0].source_name == "Bad"
    assert "network down" in errors[0].message


def test_summarize_articles_returns_article_and_global_summaries() -> None:
    now = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
    items = [article("First", "https://example.com/first", now)]

    article_summaries, global_points = summarize_articles(items, FakeSummarizer())

    assert article_summaries[0].core_viewpoint == "First core"
    assert global_points == ["共处理 1 篇文章"]
