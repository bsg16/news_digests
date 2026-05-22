# News Digest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI that reads RSS sources, fetches recent articles, summarizes them in Simplified Chinese with DeepSeek, and writes `output/YYYY-MM-DD.md`.

**Architecture:** The CLI is a thin orchestrator over focused modules: config loading, RSS parsing/fetching, pipeline filtering/deduplication, AI summarization, and Markdown rendering. Tests use fixtures and fake providers so no test requires a live network call or real API key.

**Tech Stack:** Python 3.11+, `argparse`, `dataclasses`, `feedparser`, `PyYAML`, `python-dateutil`, `python-dotenv`, `openai`, `pytest`.

---

## File Structure

- Create `pyproject.toml`: package metadata, runtime dependencies, pytest config.
- Create `README.md`: setup, config, environment, cron example, and usage.
- Create `sources.yaml.example`: researched starter RSS catalog.
- Create `news_digest/__init__.py`: package version.
- Create `news_digest/__main__.py`: `python -m news_digest` entry point.
- Create `news_digest/models.py`: shared dataclasses for sources, articles, summaries, reports, and source errors.
- Create `news_digest/config.py`: YAML loading and validation.
- Create `news_digest/rss.py`: RSS parsing and network fetch logic.
- Create `news_digest/pipeline.py`: time filtering, deduplication, source collection, and summary orchestration.
- Create `news_digest/renderer.py`: Markdown rendering and output writing.
- Create `news_digest/cli.py`: argument parsing and end-to-end command wiring.
- Create `news_digest/summarizers/__init__.py`: summarizer exports.
- Create `news_digest/summarizers/base.py`: provider protocol.
- Create `news_digest/summarizers/deepseek.py`: DeepSeek provider using OpenAI-compatible Chat Completions.
- Create `tests/fixtures/sample_feed.xml`: deterministic RSS fixture.
- Create `tests/test_config.py`: config validation tests.
- Create `tests/test_rss.py`: RSS parsing tests.
- Create `tests/test_pipeline.py`: filtering, dedupe, error-continuation, summary orchestration tests.
- Create `tests/test_renderer.py`: Markdown output tests.
- Create `tests/test_deepseek.py`: provider tests with fake client.
- Create `tests/test_cli.py`: CLI orchestration tests with monkeypatched fetcher and summarizer.

## Task 1: Project Skeleton, Models, Config, And Source Catalog

**Files:**
- Create: `pyproject.toml`
- Create: `sources.yaml.example`
- Create: `news_digest/__init__.py`
- Create: `news_digest/models.py`
- Create: `news_digest/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Create package metadata**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "news-digest"
version = "0.1.0"
description = "Fetch RSS news articles and generate a Simplified Chinese Markdown digest."
requires-python = ">=3.11"
dependencies = [
  "feedparser>=6.0.11",
  "openai>=1.0.0",
  "python-dateutil>=2.9.0",
  "python-dotenv>=1.0.1",
  "PyYAML>=6.0.2",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0",
]

[project.scripts]
news-digest = "news_digest.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 2: Write failing config tests**

Create `tests/test_config.py`:

```python
from pathlib import Path

import pytest

from news_digest.config import ConfigError, load_sources_config


def test_load_sources_config_reads_enabled_rss_sources(tmp_path: Path) -> None:
    path = tmp_path / "sources.yaml"
    path.write_text(
        """
sources:
  - name: BBC News
    type: rss
    url: http://feeds.bbci.co.uk/news/rss.xml
    enabled: true
    language: en
  - name: Disabled Feed
    type: rss
    url: https://example.com/feed.xml
    enabled: false
    language: en
""".strip(),
        encoding="utf-8",
    )

    sources = load_sources_config(path)

    assert len(sources) == 1
    assert sources[0].name == "BBC News"
    assert sources[0].type == "rss"
    assert sources[0].url == "http://feeds.bbci.co.uk/news/rss.xml"
    assert sources[0].language == "en"


def test_load_sources_config_rejects_unsupported_source_type(tmp_path: Path) -> None:
    path = tmp_path / "sources.yaml"
    path.write_text(
        """
sources:
  - name: Example Site
    type: webpage
    url: https://example.com/news
    enabled: true
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="unsupported source type"):
        load_sources_config(path)


def test_load_sources_config_missing_file_points_to_example(tmp_path: Path) -> None:
    path = tmp_path / "sources.yaml"

    with pytest.raises(ConfigError, match="sources.yaml.example"):
        load_sources_config(path)


def test_load_sources_config_rejects_missing_url(tmp_path: Path) -> None:
    path = tmp_path / "sources.yaml"
    path.write_text(
        """
sources:
  - name: Broken Feed
    type: rss
    enabled: true
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="url"):
        load_sources_config(path)
```

- [ ] **Step 3: Run config tests to verify they fail**

Run:

```bash
pytest tests/test_config.py -q
```

Expected: FAIL with `ModuleNotFoundError` or import errors for `news_digest.config`.

- [ ] **Step 4: Create models, config loader, package init, and source catalog**

Create `news_digest/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `news_digest/models.py`:

```python
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
```

Create `news_digest/config.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from news_digest.models import SourceConfig


SUPPORTED_SOURCE_TYPES = {"rss"}


class ConfigError(ValueError):
    pass


def load_sources_config(path: Path) -> list[SourceConfig]:
    if not path.exists():
        raise ConfigError(f"Config file {path} does not exist. Copy sources.yaml.example to sources.yaml first.")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError("Config root must be a mapping with a sources list.")

    raw_sources = raw.get("sources")
    if not isinstance(raw_sources, list):
        raise ConfigError("Config field sources must be a list.")

    sources: list[SourceConfig] = []
    for index, item in enumerate(raw_sources, start=1):
        if not isinstance(item, dict):
            raise ConfigError(f"Source #{index} must be a mapping.")

        source = _parse_source(index, item)
        if source.enabled:
            sources.append(source)

    return sources


def _parse_source(index: int, item: dict[str, Any]) -> SourceConfig:
    name = _required_string(index, item, "name")
    source_type = _required_string(index, item, "type")
    url = _required_string(index, item, "url")
    enabled = item.get("enabled", True)
    language = item.get("language", "en")

    if source_type not in SUPPORTED_SOURCE_TYPES:
        raise ConfigError(f"Source #{index} has unsupported source type {source_type!r}. Supported types: rss.")
    if not isinstance(enabled, bool):
        raise ConfigError(f"Source #{index} field enabled must be true or false.")
    if not isinstance(language, str) or not language.strip():
        raise ConfigError(f"Source #{index} field language must be a non-empty string.")

    return SourceConfig(
        name=name,
        type=source_type,
        url=url,
        enabled=enabled,
        language=language.strip(),
    )


def _required_string(index: int, item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"Source #{index} field {key} must be a non-empty string.")
    return value.strip()
```

Create `sources.yaml.example`:

```yaml
sources:
  - name: BBC News
    type: rss
    url: http://feeds.bbci.co.uk/news/rss.xml
    enabled: true
    language: en

  - name: BBC World
    type: rss
    url: http://feeds.bbci.co.uk/news/world/rss.xml
    enabled: true
    language: en

  - name: CNN International
    type: rss
    url: http://rss.cnn.com/rss/edition.rss
    enabled: true
    language: en

  - name: CNN World
    type: rss
    url: http://rss.cnn.com/rss/edition_world.rss
    enabled: true
    language: en

  - name: New York Times Top Stories
    type: rss
    url: https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml
    enabled: true
    language: en

  - name: New York Times World
    type: rss
    url: https://rss.nytimes.com/services/xml/rss/nyt/World.xml
    enabled: true
    language: en

  - name: The Economist Leaders
    type: rss
    url: https://www.economist.com/leaders/rss.xml
    enabled: true
    language: en

  - name: The Economist International
    type: rss
    url: https://www.economist.com/international/rss.xml
    enabled: true
    language: en

  - name: Wall Street Journal World News
    type: rss
    url: https://feeds.content.dowjones.io/public/rss/RSSWorldNews
    enabled: true
    language: en

  - name: Wall Street Journal Markets
    type: rss
    url: https://feeds.content.dowjones.io/public/rss/RSSMarketsMain
    enabled: true
    language: en

  - name: Global Times Candidate
    type: rss
    url: https://www.globaltimes.cn/rss/outbrain.xml
    enabled: false
    language: en
```

- [ ] **Step 5: Run config tests to verify they pass**

Run:

```bash
pytest tests/test_config.py -q
```

Expected: PASS with `4 passed`.

- [ ] **Step 6: Commit Task 1**

Run:

```bash
git add pyproject.toml sources.yaml.example news_digest/__init__.py news_digest/models.py news_digest/config.py tests/test_config.py
git commit -m "feat: add config loading and source catalog"
```

## Task 2: RSS Parsing And Fetching

**Files:**
- Create: `news_digest/rss.py`
- Create: `tests/fixtures/sample_feed.xml`
- Test: `tests/test_rss.py`

- [ ] **Step 1: Write RSS fixture**

Create `tests/fixtures/sample_feed.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example Feed</title>
    <item>
      <title>First Story</title>
      <link>https://example.com/first</link>
      <author>Reporter One</author>
      <pubDate>Fri, 22 May 2026 04:00:00 GMT</pubDate>
      <description><![CDATA[<p>First story summary with <strong>markup</strong>.</p>]]></description>
    </item>
    <item>
      <title>Second Story</title>
      <link>https://example.com/second?utm_source=rss</link>
      <pubDate>Thu, 21 May 2026 03:00:00 GMT</pubDate>
      <description>Second story summary.</description>
    </item>
  </channel>
</rss>
```

- [ ] **Step 2: Write failing RSS parser tests**

Create `tests/test_rss.py`:

```python
from pathlib import Path

from news_digest.models import SourceConfig
from news_digest.rss import parse_feed_text


def test_parse_feed_text_normalizes_entries() -> None:
    source = SourceConfig(
        name="Example Feed",
        type="rss",
        url="https://example.com/feed.xml",
        enabled=True,
        language="en",
    )
    xml = Path("tests/fixtures/sample_feed.xml").read_text(encoding="utf-8")

    articles = parse_feed_text(source, xml)

    assert len(articles) == 2
    assert articles[0].source_name == "Example Feed"
    assert articles[0].title == "First Story"
    assert articles[0].url == "https://example.com/first"
    assert articles[0].author == "Reporter One"
    assert articles[0].published_at is not None
    assert articles[0].published_at.isoformat() == "2026-05-22T04:00:00+00:00"
    assert articles[0].source_text == "First story summary with markup."


def test_parse_feed_text_skips_entries_without_link() -> None:
    source = SourceConfig(name="Broken", type="rss", url="https://example.com/rss", enabled=True, language="en")
    xml = """
<rss version="2.0">
  <channel>
    <item>
      <title>Missing Link</title>
      <description>Cannot use this item.</description>
    </item>
  </channel>
</rss>
"""

    assert parse_feed_text(source, xml) == []
```

- [ ] **Step 3: Run RSS tests to verify they fail**

Run:

```bash
pytest tests/test_rss.py -q
```

Expected: FAIL with import error for `news_digest.rss`.

- [ ] **Step 4: Implement RSS parsing and fetching**

Create `news_digest/rss.py`:

```python
from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import feedparser

from news_digest.models import Article, SourceConfig


USER_AGENT = "news-digest/0.1 (+https://local)"


class FeedFetchError(RuntimeError):
    pass


def fetch_source_articles(source: SourceConfig, timeout_seconds: int = 20) -> list[Article]:
    request = Request(source.url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
    except URLError as exc:
        raise FeedFetchError(f"Failed to fetch {source.name}: {exc}") from exc

    text = raw.decode("utf-8", errors="replace")
    return parse_feed_text(source, text)


def parse_feed_file(source: SourceConfig, path: Path) -> list[Article]:
    return parse_feed_text(source, path.read_text(encoding="utf-8"))


def parse_feed_text(source: SourceConfig, text: str) -> list[Article]:
    parsed = feedparser.parse(text)
    articles: list[Article] = []

    for entry in parsed.entries:
        title = _clean_text(entry.get("title", ""))
        url = _clean_text(entry.get("link", ""))
        if not title or not url:
            continue

        articles.append(
            Article(
                source_name=source.name,
                title=title,
                url=url,
                published_at=_entry_datetime(entry),
                author=_optional_clean(entry.get("author")),
                source_text=_entry_text(entry),
            )
        )

    return articles


def _entry_datetime(entry: object) -> datetime | None:
    published = getattr(entry, "published", None) or getattr(entry, "updated", None)
    if isinstance(published, str) and published.strip():
        try:
            parsed = parsedate_to_datetime(published)
        except (TypeError, ValueError):
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    published_parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if published_parsed:
        return datetime(*published_parsed[:6], tzinfo=timezone.utc)

    return None


def _entry_text(entry: object) -> str:
    summary = getattr(entry, "summary", None)
    if isinstance(summary, str) and summary.strip():
        return _clean_text(summary)

    content = getattr(entry, "content", None)
    if isinstance(content, list) and content:
        value = content[0].get("value", "") if isinstance(content[0], dict) else ""
        return _clean_text(value)

    return ""


def _optional_clean(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = _clean_text(value)
    return cleaned or None


def _clean_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    normalized = re.sub(r"\s+", " ", unescape(without_tags)).strip()
    return normalized
```

- [ ] **Step 5: Run RSS tests to verify they pass**

Run:

```bash
pytest tests/test_rss.py -q
```

Expected: PASS with `2 passed`.

- [ ] **Step 6: Commit Task 2**

Run:

```bash
git add news_digest/rss.py tests/fixtures/sample_feed.xml tests/test_rss.py
git commit -m "feat: add RSS parsing"
```

## Task 3: Pipeline Filtering, Deduplication, Error Continuation, And Summarization Flow

**Files:**
- Create: `news_digest/pipeline.py`
- Create: `news_digest/summarizers/base.py`
- Modify: `news_digest/summarizers/__init__.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing pipeline tests**

Create `tests/test_pipeline.py`:

```python
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
```

- [ ] **Step 2: Run pipeline tests to verify they fail**

Run:

```bash
pytest tests/test_pipeline.py -q
```

Expected: FAIL with import error for `news_digest.pipeline`.

- [ ] **Step 3: Implement summarizer protocol and pipeline**

Create `news_digest/summarizers/base.py`:

```python
from __future__ import annotations

from typing import Protocol

from news_digest.models import Article, ArticleSummary


class Summarizer(Protocol):
    def summarize_article(self, item: Article) -> ArticleSummary:
        raise NotImplementedError

    def summarize_global_key_points(self, summaries: list[ArticleSummary]) -> list[str]:
        raise NotImplementedError
```

Create `news_digest/summarizers/__init__.py`:

```python
from news_digest.summarizers.base import Summarizer

__all__ = ["Summarizer"]
```

Create `news_digest/pipeline.py`:

```python
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
```

- [ ] **Step 4: Run pipeline tests to verify they pass**

Run:

```bash
pytest tests/test_pipeline.py -q
```

Expected: PASS with `4 passed`.

- [ ] **Step 5: Commit Task 3**

Run:

```bash
git add news_digest/pipeline.py news_digest/summarizers/__init__.py news_digest/summarizers/base.py tests/test_pipeline.py
git commit -m "feat: add digest pipeline"
```

## Task 4: Markdown Rendering And Output Writing

**Files:**
- Create: `news_digest/renderer.py`
- Test: `tests/test_renderer.py`

- [ ] **Step 1: Write failing renderer tests**

Create `tests/test_renderer.py`:

```python
from datetime import datetime, timezone
from pathlib import Path

from news_digest.models import Article, ArticleSummary, DigestReport, SourceError
from news_digest.renderer import output_path_for, render_markdown, write_report


def summary(source_name: str, title: str) -> ArticleSummary:
    return ArticleSummary(
        article=Article(
            source_name=source_name,
            title=title,
            url="https://example.com/article",
            published_at=datetime(2026, 5, 22, 8, 15, tzinfo=timezone.utc),
            author=None,
            source_text="source text",
        ),
        core_viewpoint="这是核心观点。",
        key_points=["第一条关键信息。", "第二条关键信息。"],
        tags=["国际", "经济"],
    )


def test_render_markdown_uses_required_article_format() -> None:
    report = DigestReport(
        generated_at=datetime(2026, 5, 22, 19, 30, tzinfo=timezone.utc),
        window_hours=24,
        article_summaries=[summary("BBC News", "总统保留其他多项权力以征收进口税")],
        global_key_points=["全球贸易政策仍存在不确定性。"],
    )

    markdown = render_markdown(report)

    assert markdown.startswith("# 新闻日报 - 2026-05-22")
    assert "## 全局要点\n\n- 全球贸易政策仍存在不确定性。" in markdown
    assert "## BBC News" in markdown
    assert "### 总统保留其他多项权力以征收进口税" in markdown
    assert "- **核心观点**：这是核心观点。" in markdown
    assert "- **关键信息**：\n    - 第一条关键信息。\n    - 第二条关键信息。" in markdown
    assert "- **标签**：国际、经济" in markdown


def test_render_markdown_handles_empty_report_and_source_errors() -> None:
    report = DigestReport(
        generated_at=datetime(2026, 5, 22, 19, 30, tzinfo=timezone.utc),
        window_hours=24,
        article_summaries=[],
        source_errors=[SourceError(source_name="Broken", message="network down")],
    )

    markdown = render_markdown(report)

    assert "过去 24 小时内没有找到可摘要的文章。" in markdown
    assert "## 抓取警告" in markdown
    assert "- Broken: network down" in markdown


def test_write_report_uses_date_filename(tmp_path: Path) -> None:
    report = DigestReport(
        generated_at=datetime(2026, 5, 22, 19, 30, tzinfo=timezone.utc),
        window_hours=24,
        article_summaries=[summary("BBC News", "Story")],
    )

    path = write_report(report, tmp_path)

    assert path == tmp_path / "2026-05-22.md"
    assert path.read_text(encoding="utf-8").startswith("# 新闻日报 - 2026-05-22")


def test_output_path_for_uses_generated_date(tmp_path: Path) -> None:
    generated_at = datetime(2026, 5, 22, 19, 30, tzinfo=timezone.utc)

    assert output_path_for(tmp_path, generated_at) == tmp_path / "2026-05-22.md"
```

- [ ] **Step 2: Run renderer tests to verify they fail**

Run:

```bash
pytest tests/test_renderer.py -q
```

Expected: FAIL with import error for `news_digest.renderer`.

- [ ] **Step 3: Implement Markdown renderer**

Create `news_digest/renderer.py`:

```python
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path

from news_digest.models import ArticleSummary, DigestReport


def render_markdown(report: DigestReport) -> str:
    date_text = report.generated_at.date().isoformat()
    generated_text = report.generated_at.strftime("%Y-%m-%d %H:%M %Z").strip()
    lines: list[str] = [
        f"# 新闻日报 - {date_text}",
        "",
        f"生成时间：{generated_text}",
        f"范围：过去 {report.window_hours} 小时",
        "",
        "## 全局要点",
        "",
    ]

    if report.global_key_points:
        lines.extend(f"- {point}" for point in report.global_key_points)
    else:
        lines.append("- 过去 24 小时内没有找到可摘要的文章。")

    if report.source_errors:
        lines.extend(["", "## 抓取警告", ""])
        lines.extend(f"- {error.source_name}: {error.message}" for error in report.source_errors)

    grouped = _group_by_source(report.article_summaries)
    for source_name, summaries in grouped.items():
        lines.extend(["", f"## {source_name}", ""])
        for item in summaries:
            lines.extend(_render_article_summary(item))

    return "\n".join(lines).rstrip() + "\n"


def write_report(report: DigestReport, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_path_for(output_dir, report.generated_at)
    path.write_text(render_markdown(report), encoding="utf-8")
    return path


def output_path_for(output_dir: Path, generated_at: datetime) -> Path:
    return output_dir / f"{generated_at.date().isoformat()}.md"


def _group_by_source(summaries: list[ArticleSummary]) -> dict[str, list[ArticleSummary]]:
    grouped: dict[str, list[ArticleSummary]] = defaultdict(list)
    for item in summaries:
        grouped[item.article.source_name].append(item)
    return dict(grouped)


def _render_article_summary(item: ArticleSummary) -> list[str]:
    published = item.article.published_at.strftime("%Y-%m-%d %H:%M") if item.article.published_at else "未知"
    lines = [
        f"### {item.article.title}",
        "",
        f"- **核心观点**：{item.core_viewpoint}",
        "- **关键信息**：",
    ]
    lines.extend(f"    - {point}" for point in item.key_points)
    lines.extend(
        [
            f"- **标签**：{'、'.join(item.tags)}",
            f"- 链接：{item.article.url}",
            f"- 发布时间：{published}",
            "",
        ]
    )
    return lines
```

- [ ] **Step 4: Run renderer tests to verify they pass**

Run:

```bash
pytest tests/test_renderer.py -q
```

Expected: PASS with `4 passed`.

- [ ] **Step 5: Commit Task 4**

Run:

```bash
git add news_digest/renderer.py tests/test_renderer.py
git commit -m "feat: render markdown digest"
```

## Task 5: DeepSeek Summarizer Provider

**Files:**
- Create: `news_digest/summarizers/deepseek.py`
- Modify: `news_digest/summarizers/__init__.py`
- Test: `tests/test_deepseek.py`

- [ ] **Step 1: Write failing DeepSeek provider tests**

Create `tests/test_deepseek.py`:

```python
from datetime import datetime, timezone

from news_digest.models import Article, ArticleSummary
from news_digest.summarizers.deepseek import DEFAULT_MODEL, DeepSeekSummarizer


class FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = FakeMessage(content)


class FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [FakeChoice(content)]


class FakeCompletions:
    def __init__(self) -> None:
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if "全局要点" in kwargs["messages"][1]["content"]:
            return FakeResponse('{"global_key_points":["第一条全局要点","第二条全局要点"]}')
        return FakeResponse(
            '{"core_viewpoint":"核心观点文本","key_points":["要点一","要点二"],"tags":["政治","贸易"]}'
        )


class FakeChat:
    def __init__(self) -> None:
        self.completions = FakeCompletions()


class FakeClient:
    def __init__(self) -> None:
        self.chat = FakeChat()


def sample_article() -> Article:
    return Article(
        source_name="BBC News",
        title="Trade story",
        url="https://example.com/trade",
        published_at=datetime(2026, 5, 22, 4, 0, tzinfo=timezone.utc),
        author=None,
        source_text="A story about trade policy.",
    )


def test_deepseek_summarizer_uses_default_model_and_parses_article_json() -> None:
    client = FakeClient()
    summarizer = DeepSeekSummarizer(api_key="test-key", client=client)

    result = summarizer.summarize_article(sample_article())

    assert DEFAULT_MODEL == "deepseek-v4-flash"
    assert result.core_viewpoint == "核心观点文本"
    assert result.key_points == ["要点一", "要点二"]
    assert result.tags == ["政治", "贸易"]
    call = client.chat.completions.calls[0]
    assert call["model"] == "deepseek-v4-flash"
    assert call["response_format"] == {"type": "json_object"}


def test_deepseek_summarizer_parses_global_key_points() -> None:
    client = FakeClient()
    summarizer = DeepSeekSummarizer(api_key="test-key", client=client)
    article_summary = ArticleSummary(
        article=sample_article(),
        core_viewpoint="核心观点文本",
        key_points=["要点一"],
        tags=["政治"],
    )

    result = summarizer.summarize_global_key_points([article_summary])

    assert result == ["第一条全局要点", "第二条全局要点"]
```

- [ ] **Step 2: Run DeepSeek tests to verify they fail**

Run:

```bash
pytest tests/test_deepseek.py -q
```

Expected: FAIL with import error for `news_digest.summarizers.deepseek`.

- [ ] **Step 3: Implement DeepSeek provider**

Create `news_digest/summarizers/deepseek.py`:

```python
from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from news_digest.models import Article, ArticleSummary


DEFAULT_MODEL = "deepseek-v4-flash"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class SummaryParseError(ValueError):
    pass


class DeepSeekSummarizer:
    def __init__(self, *, api_key: str, model: str = DEFAULT_MODEL, client: Any | None = None) -> None:
        if not api_key.strip():
            raise ValueError("DeepSeek API key must not be empty.")
        self.model = model
        self.client = client or OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)

    def summarize_article(self, item: Article) -> ArticleSummary:
        payload = self._json_completion(_article_prompt(item))
        return ArticleSummary(
            article=item,
            core_viewpoint=_required_string(payload, "core_viewpoint"),
            key_points=_required_string_list(payload, "key_points"),
            tags=_required_string_list(payload, "tags"),
        )

    def summarize_global_key_points(self, summaries: list[ArticleSummary]) -> list[str]:
        if not summaries:
            return []
        payload = self._json_completion(_global_prompt(summaries))
        return _required_string_list(payload, "global_key_points")

    def _json_completion(self, user_prompt: str) -> dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "你是严谨的中文新闻摘要编辑。只输出合法 JSON，不输出 Markdown。",
                },
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = response.choices[0].message.content
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise SummaryParseError(f"Model returned invalid JSON: {content}") from exc
        if not isinstance(parsed, dict):
            raise SummaryParseError("Model JSON response must be an object.")
        return parsed


def _article_prompt(item: Article) -> str:
    return f"""
请将下面新闻文章摘要为简体中文。输出 JSON，字段必须为：
- core_viewpoint: 字符串，一句话概括核心观点
- key_points: 字符串数组，3 到 5 条关键信息
- tags: 字符串数组，2 到 5 个中文标签

标题：{item.title}
来源：{item.source_name}
链接：{item.url}
正文或 RSS 摘要：{item.source_text}
""".strip()


def _global_prompt(summaries: list[ArticleSummary]) -> str:
    lines = ["请基于以下文章摘要生成 3 到 6 条简体中文全局要点。输出 JSON，字段为 global_key_points。", ""]
    for item in summaries:
        lines.append(f"- {item.article.source_name} / {item.article.title}: {item.core_viewpoint}")
    return "\n".join(lines)


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SummaryParseError(f"Model JSON field {key} must be a non-empty string.")
    return value.strip()


def _required_string_list(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise SummaryParseError(f"Model JSON field {key} must be a list.")
    result = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if not result:
        raise SummaryParseError(f"Model JSON field {key} must contain at least one string.")
    return result
```

Modify `news_digest/summarizers/__init__.py`:

```python
from news_digest.summarizers.base import Summarizer
from news_digest.summarizers.deepseek import DEFAULT_MODEL, DeepSeekSummarizer

__all__ = ["DEFAULT_MODEL", "DeepSeekSummarizer", "Summarizer"]
```

- [ ] **Step 4: Run DeepSeek tests to verify they pass**

Run:

```bash
pytest tests/test_deepseek.py -q
```

Expected: PASS with `2 passed`.

- [ ] **Step 5: Commit Task 5**

Run:

```bash
git add news_digest/summarizers/__init__.py news_digest/summarizers/deepseek.py tests/test_deepseek.py
git commit -m "feat: add DeepSeek summarizer"
```

## Task 6: CLI Integration

**Files:**
- Create: `news_digest/__main__.py`
- Create: `news_digest/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_cli.py`:

```python
from datetime import datetime, timezone
from pathlib import Path

import pytest

from news_digest import cli
from news_digest.models import Article, ArticleSummary


class FakeSummarizer:
    def summarize_article(self, item: Article) -> ArticleSummary:
        return ArticleSummary(
            article=item,
            core_viewpoint="核心观点",
            key_points=["关键信息"],
            tags=["标签"],
        )

    def summarize_global_key_points(self, summaries: list[ArticleSummary]) -> list[str]:
        return ["全局要点"]


def test_cli_fails_before_fetch_without_api_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "sources.yaml"
    config_path.write_text(
        """
sources:
  - name: Example
    type: rss
    url: https://example.com/feed.xml
    enabled: true
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(SystemExit) as exc:
        cli.main(["run", "--config", str(config_path), "--output-dir", str(tmp_path / "out")])

    assert exc.value.code == 2


def test_cli_run_writes_markdown_with_monkeypatched_dependencies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "sources.yaml"
    output_dir = tmp_path / "output"
    config_path.write_text(
        """
sources:
  - name: Example
    type: rss
    url: https://example.com/feed.xml
    enabled: true
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(cli, "build_summarizer", lambda api_key, model: FakeSummarizer())
    monkeypatch.setattr(
        cli,
        "fetch_source_articles",
        lambda source: [
            Article(
                source_name=source.name,
                title="Story",
                url="https://example.com/story",
                published_at=datetime(2026, 5, 22, 8, 0, tzinfo=timezone.utc),
                author=None,
                source_text="Story text",
            )
        ],
    )

    code = cli.main(
        [
            "run",
            "--config",
            str(config_path),
            "--output-dir",
            str(output_dir),
            "--now",
            "2026-05-22T12:00:00+00:00",
        ]
    )

    assert code == 0
    output = (output_dir / "2026-05-22.md").read_text(encoding="utf-8")
    assert "### Story" in output
    assert "- **核心观点**：核心观点" in output
```

- [ ] **Step 2: Run CLI tests to verify they fail**

Run:

```bash
pytest tests/test_cli.py -q
```

Expected: FAIL with import error for `news_digest.cli`.

- [ ] **Step 3: Implement CLI**

Create `news_digest/cli.py`:

```python
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from news_digest.config import ConfigError, load_sources_config
from news_digest.models import DigestReport
from news_digest.pipeline import collect_recent_articles, summarize_articles
from news_digest.renderer import write_report
from news_digest.rss import fetch_source_articles
from news_digest.summarizers.deepseek import DEFAULT_MODEL, DeepSeekSummarizer


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command != "run":
        parser.print_help()
        return 0

    load_dotenv()

    try:
        sources = load_sources_config(args.config)
    except ConfigError as exc:
        parser.exit(2, f"config error: {exc}\n")

    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        parser.exit(2, "config error: DEEPSEEK_API_KEY is required for the DeepSeek summarizer.\n")

    model = os.getenv("NEWS_DIGEST_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    summarizer = build_summarizer(api_key, model)
    now = parse_now(args.now)

    articles, source_errors = collect_recent_articles(
        sources,
        now=now,
        window_hours=args.window_hours,
        fetcher=fetch_source_articles,
    )
    article_summaries, global_points = summarize_articles(articles, summarizer)
    report = DigestReport(
        generated_at=now,
        window_hours=args.window_hours,
        article_summaries=article_summaries,
        global_key_points=global_points,
        source_errors=source_errors,
    )

    path = write_report(report, args.output_dir)
    print(f"Wrote {path}")
    if source_errors:
        print(f"Completed with {len(source_errors)} source warning(s)", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="news-digest")
    subparsers = parser.add_subparsers(dest="command")
    run = subparsers.add_parser("run", help="Generate a Markdown news digest.")
    run.add_argument("--config", type=Path, default=Path("sources.yaml"))
    run.add_argument("--output-dir", type=Path, default=Path("output"))
    run.add_argument("--window-hours", type=int, default=24)
    run.add_argument("--now", default=None, help="ISO timestamp for reproducible runs.")
    return parser


def build_summarizer(api_key: str, model: str) -> DeepSeekSummarizer:
    return DeepSeekSummarizer(api_key=api_key, model=model)


def parse_now(value: str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
```

Create `news_digest/__main__.py`:

```python
from news_digest.cli import main


raise SystemExit(main())
```

- [ ] **Step 4: Run CLI tests to verify they pass**

Run:

```bash
pytest tests/test_cli.py -q
```

Expected: PASS with `2 passed`.

- [ ] **Step 5: Commit Task 6**

Run:

```bash
git add news_digest/__main__.py news_digest/cli.py tests/test_cli.py
git commit -m "feat: add news digest CLI"
```

## Task 7: Documentation And Full Verification

**Files:**
- Create: `README.md`
- Create: `.env.example`
- Modify: `.gitignore`

- [ ] **Step 1: Create user documentation**

Create `README.md`:

```markdown
# News Digest

Fetch RSS articles from configured news sources, summarize them in Simplified Chinese with DeepSeek, and write a Markdown daily report to `output/YYYY-MM-DD.md`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp sources.yaml.example sources.yaml
cp .env.example .env
```

Edit `.env` and set `DEEPSEEK_API_KEY`.

## Run

```bash
news-digest run
```

Equivalent module command:

```bash
python -m news_digest run
```

## Configuration

RSS sources live in `sources.yaml`. The provided `sources.yaml.example` includes starter feeds for BBC, CNN, New York Times, The Economist, Wall Street Journal, and a disabled Global Times candidate.

The Global Times candidate is disabled because the accessible RSS feed is titled `outbrain` and may not provide stable daily coverage. The Economist and Wall Street Journal feeds may contain only RSS summaries or links to paywalled articles; this tool summarizes only feed text that is available in RSS.

## Environment

- `DEEPSEEK_API_KEY`: required.
- `NEWS_DIGEST_MODEL`: optional, defaults to `deepseek-v4-flash`.

## Cron Example

Run every day at 08:00 server time:

```cron
0 8 * * * cd /Users/fangqian/deploy/news_digests && /Users/fangqian/deploy/news_digests/.venv/bin/news-digest run >> /Users/fangqian/deploy/news_digests/news-digest.log 2>&1
```

## Test

```bash
pytest
```
```

Create `.env.example`:

```bash
DEEPSEEK_API_KEY=
NEWS_DIGEST_MODEL=deepseek-v4-flash
```

Ensure `.gitignore` contains:

```gitignore
.env
.env.*
!.env.example

.venv/
__pycache__/
.pytest_cache/

output/

.agents/
plugins/
```

- [ ] **Step 2: Run focused tests**

Run:

```bash
pytest tests/test_config.py tests/test_rss.py tests/test_pipeline.py tests/test_renderer.py tests/test_deepseek.py tests/test_cli.py -q
```

Expected: PASS with all tests passing.

- [ ] **Step 3: Run package help command**

Run:

```bash
python -m news_digest --help
```

Expected: output includes `usage: news-digest`.

- [ ] **Step 4: Commit Task 7**

Run:

```bash
git add README.md .env.example .gitignore
git commit -m "docs: add setup and cron instructions"
```

## Task 8: Final End-To-End Smoke Test With Fake Dependencies

**Files:**
- No new files required.

- [ ] **Step 1: Install the package in editable mode**

Run:

```bash
python -m pip install -e ".[dev]"
```

Expected: package installs without dependency resolution errors.

- [ ] **Step 2: Run the full automated test suite**

Run:

```bash
pytest -q
```

Expected: PASS with every test passing.

- [ ] **Step 3: Check tracked files and secret hygiene**

Run:

```bash
git status --short
git grep -n "sk-" || true
```

Expected: `git status --short` prints no tracked modifications. `git grep` prints no API keys.

## Self-Review

- Spec coverage: config loading, researched RSS catalog, RSS parsing, 24-hour filtering, deduplication, DeepSeek default model, Simplified Chinese article format, global key points, grouped Markdown output, source-error continuation, missing API key failure, `.env` secret hygiene, and cron documentation all map to tasks above.
- Marker scan: no unresolved implementation markers remain.
- Type consistency: the plan consistently uses `SourceConfig`, `Article`, `ArticleSummary`, `SourceError`, `DigestReport`, `Summarizer`, and `DeepSeekSummarizer` across tests and implementation.
