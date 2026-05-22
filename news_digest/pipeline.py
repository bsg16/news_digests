from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from news_digest.models import Article, ArticleSummary, SourceConfig, SourceError
from news_digest.summarizers.base import Summarizer


TRACKING_PREFIXES = ("utm_",)
TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


def collect_recent_articles(
    sources: list[SourceConfig],
    *,
    now: datetime,
    window_hours: int,
    fetcher,
) -> tuple[list[Article], list[SourceError]]:
    articles: list[Article] = []
    errors: list[SourceError] = []

    for source in sources:
        try:
            articles.extend(fetcher(source))
        except Exception as exc:
            errors.append(SourceError(source_name=source.name, message=str(exc)))

    filtered = filter_articles_by_window(articles, now=now, window_hours=window_hours)
    return deduplicate_articles(filtered), errors


def filter_articles_by_window(articles: list[Article], *, now: datetime, window_hours: int) -> list[Article]:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    cutoff = now.astimezone(timezone.utc) - timedelta(hours=window_hours)

    result: list[Article] = []
    for item in articles:
        if item.published_at is None:
            result.append(item)
            continue

        published = item.published_at
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        if published.astimezone(timezone.utc) >= cutoff:
            result.append(item)

    return result


def deduplicate_articles(articles: list[Article]) -> list[Article]:
    seen: set[str] = set()
    unique: list[Article] = []

    for item in articles:
        key = canonical_article_key(item)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    return unique


def canonical_article_key(item: Article) -> str:
    if item.url:
        return f"url:{_canonical_url(item.url)}"
    return f"title:{item.source_name.lower()}:{item.title.strip().lower()}"


def summarize_articles(
    articles: list[Article],
    summarizer: Summarizer,
) -> tuple[list[ArticleSummary], list[str]]:
    summaries: list[ArticleSummary] = []

    for item in articles:
        summaries.append(summarizer.summarize_article(item))

    global_points = summarizer.summarize_global_key_points(summaries) if summaries else []
    return summaries, global_points


def _canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key not in TRACKING_KEYS and not key.startswith(TRACKING_PREFIXES)
    ]
    query = urlencode(query_pairs, doseq=True)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), query, ""))
