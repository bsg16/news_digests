from __future__ import annotations

from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

import feedparser
from dateutil import parser as date_parser

from news_digest.models import Article, SourceConfig

USER_AGENT = "news-digest/0.1 (+https://local)"
_BOUNDARY_TAGS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "br",
    "dd",
    "div",
    "dl",
    "dt",
    "figcaption",
    "figure",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "td",
    "th",
    "tr",
    "ul",
}


class FeedFetchError(RuntimeError):
    pass


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        self._chunks.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in _BOUNDARY_TAGS:
            self._chunks.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in _BOUNDARY_TAGS:
            self._chunks.append(" ")

    def get_text(self) -> str:
        return "".join(self._chunks)


def fetch_source_articles(source: SourceConfig, timeout_seconds: int = 20) -> list[Article]:
    request = Request(source.url, headers={"User-Agent": USER_AGENT})

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            data = response.read()
    except URLError as error:
        raise FeedFetchError(f"failed to fetch {source.name}: {error}") from error

    return parse_feed_bytes(source, data)


def parse_feed_file(source: SourceConfig, path: Path) -> list[Article]:
    return parse_feed_text(source, path.read_text(encoding="utf-8"))


def parse_feed_bytes(source: SourceConfig, data: bytes) -> list[Article]:
    return _articles_from_feed(source, feedparser.parse(data))


def parse_feed_text(source: SourceConfig, text: str) -> list[Article]:
    return _articles_from_feed(source, feedparser.parse(text))


def _articles_from_feed(source: SourceConfig, feed: Any) -> list[Article]:
    articles: list[Article] = []

    for entry in feed.entries:
        title = _optional_clean(_entry_text(entry, "title"))
        link = _optional_clean(_entry_text(entry, "link"))

        if title is None or link is None:
            continue

        articles.append(
            Article(
                source_name=source.name,
                title=title,
                url=link,
                published_at=_entry_datetime(entry),
                author=_optional_clean(_entry_text(entry, "author")),
                source_text=_clean_text(_entry_text(entry, "summary", "description")),
            )
        )

    return articles


def _entry_datetime(entry: Any) -> datetime | None:
    for parsed_key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(parsed_key)
        if parsed is not None:
            return datetime(*parsed[:6], tzinfo=timezone.utc)

    for text_key in ("published", "updated", "pubDate"):
        value = _entry_text(entry, text_key)
        if not value:
            continue
        try:
            parsed_datetime = date_parser.parse(value)
        except (TypeError, ValueError, OverflowError):
            continue
        if parsed_datetime.tzinfo is None:
            parsed_datetime = parsed_datetime.replace(tzinfo=timezone.utc)
        return parsed_datetime.astimezone(timezone.utc)

    return None


def _entry_text(entry: Any, *keys: str) -> str:
    for key in keys:
        value = entry.get(key)
        if value is None:
            continue
        return str(value)
    return ""


def _optional_clean(value: str) -> str | None:
    cleaned = _clean_text(value)
    return cleaned or None


def _clean_text(value: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(value)
    parser.close()
    return " ".join(parser.get_text().split())
