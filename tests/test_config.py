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
