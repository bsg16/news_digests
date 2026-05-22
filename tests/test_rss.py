from pathlib import Path
from urllib.error import URLError

import pytest

import news_digest.rss as rss
from news_digest.models import SourceConfig
from news_digest.rss import FeedFetchError, fetch_source_articles, parse_feed_bytes, parse_feed_file, parse_feed_text


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
    assert articles[1].source_name == "Example Feed"
    assert articles[1].title == "Second Story"
    assert articles[1].url == "https://example.com/second?utm_source=rss"
    assert articles[1].author is None
    assert articles[1].published_at is not None
    assert articles[1].published_at.isoformat() == "2026-05-21T03:00:00+00:00"
    assert articles[1].source_text == "Second story summary."


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


def test_parse_feed_bytes_honors_xml_encoding_declaration() -> None:
    source = SourceConfig(name="Encoded", type="rss", url="https://example.com/feed.xml", enabled=True, language="en")
    xml = """<?xml version="1.0" encoding="ISO-8859-1"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Café</title>
      <link>https://example.com/cafe</link>
      <description>Café summary.</description>
    </item>
  </channel>
</rss>
"""

    articles = parse_feed_bytes(source, xml.encode("iso-8859-1"))

    assert len(articles) == 1
    assert articles[0].title == "Café"
    assert articles[0].source_text == "Café summary."


def test_parse_feed_file_honors_xml_encoding_declaration(tmp_path: Path) -> None:
    source = SourceConfig(name="Encoded File", type="rss", url="https://example.com/feed.xml", enabled=True, language="en")
    xml = """<?xml version="1.0" encoding="ISO-8859-1"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Café</title>
      <link>https://example.com/cafe-file</link>
      <description>Café file summary.</description>
    </item>
  </channel>
</rss>
"""
    path = tmp_path / "feed.xml"
    path.write_bytes(xml.encode("iso-8859-1"))

    articles = parse_feed_file(source, path)

    assert len(articles) == 1
    assert articles[0].title == "Café"
    assert articles[0].source_text == "Café file summary."


def test_parse_feed_text_preserves_html_block_and_break_boundaries() -> None:
    source = SourceConfig(name="HTML", type="rss", url="https://example.com/feed.xml", enabled=True, language="en")
    xml = """
<rss version="2.0">
  <channel>
    <item>
      <title>HTML Story</title>
      <link>https://example.com/html</link>
      <description><![CDATA[<p>Hello</p><p>World</p>one<br>two]]></description>
    </item>
  </channel>
</rss>
"""

    articles = parse_feed_text(source, xml)

    assert articles[0].source_text == "Hello World one two"


def test_fetch_source_articles_uses_user_agent_timeout_and_raw_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    source = SourceConfig(name="Fetch", type="rss", url="https://example.com/feed.xml", enabled=True, language="en")
    xml = """<?xml version="1.0" encoding="ISO-8859-1"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Café</title>
      <link>https://example.com/cafe</link>
      <description>Café summary.</description>
    </item>
  </channel>
</rss>
"""
    calls = []

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def read(self) -> bytes:
            return xml.encode("iso-8859-1")

    def fake_urlopen(request: object, timeout: int) -> FakeResponse:
        calls.append((request, timeout))
        return FakeResponse()

    monkeypatch.setattr(rss, "urlopen", fake_urlopen)

    articles = fetch_source_articles(source, timeout_seconds=7)

    assert len(articles) == 1
    assert articles[0].title == "Café"
    request, timeout = calls[0]
    assert timeout == 7
    assert request.get_header("User-agent") == rss.USER_AGENT


def test_fetch_source_articles_wraps_url_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    source = SourceConfig(name="Broken", type="rss", url="https://example.com/feed.xml", enabled=True, language="en")

    def fake_urlopen(request: object, timeout: int) -> object:
        raise URLError("no route")

    monkeypatch.setattr(rss, "urlopen", fake_urlopen)

    with pytest.raises(FeedFetchError, match="failed to fetch Broken") as exc_info:
        fetch_source_articles(source)

    assert isinstance(exc_info.value.__cause__, URLError)


def test_fetch_source_articles_wraps_timeouts(monkeypatch: pytest.MonkeyPatch) -> None:
    source = SourceConfig(name="Slow", type="rss", url="https://example.com/feed.xml", enabled=True, language="en")

    def fake_urlopen(request: object, timeout: int) -> object:
        raise TimeoutError("timed out")

    monkeypatch.setattr(rss, "urlopen", fake_urlopen)

    with pytest.raises(FeedFetchError, match="failed to fetch Slow") as exc_info:
        fetch_source_articles(source)

    assert isinstance(exc_info.value.__cause__, TimeoutError)
