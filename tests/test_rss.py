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
