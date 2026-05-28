from datetime import datetime, timezone
from pathlib import Path

import pytest

from news_digest import cli
from news_digest.models import Article, ArticleSummary, TopicSummary


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

    def merge_topic_summaries(self, candidates: list[TopicSummary]) -> list[TopicSummary]:
        return candidates


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
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(
        cli,
        "fetch_source_articles",
        lambda source: pytest.fail("fetch_source_articles must not be called without an API key"),
    )

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


def test_parse_now_default_returns_local_aware_datetime() -> None:
    now = cli.parse_now(None)

    assert now.tzinfo is not None
    assert now.utcoffset() is not None
    assert now.utcoffset() == datetime.now().astimezone().utcoffset()


def test_parse_now_preserves_provided_aware_timestamp() -> None:
    now = cli.parse_now("2026-05-23T00:30:00+08:00")

    assert now == datetime.fromisoformat("2026-05-23T00:30:00+08:00")
    assert now.tzinfo is not None
    assert now.utcoffset() == datetime.fromisoformat("2026-05-23T00:30:00+08:00").utcoffset()


def test_parse_now_treats_naive_timestamp_as_local_aware_datetime() -> None:
    now = cli.parse_now("2026-05-23T00:30:00")

    assert now.tzinfo is not None
    assert now.utcoffset() is not None
    assert now.replace(tzinfo=None) == datetime(2026, 5, 23, 0, 30)
    assert now.utcoffset() == datetime(2026, 5, 23, 0, 30).astimezone().utcoffset()


def test_cli_run_uses_provided_aware_timestamp_date_for_output_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(cli, "build_summarizer", lambda api_key, model: FakeSummarizer())
    monkeypatch.setattr(
        cli,
        "fetch_source_articles",
        lambda source: [
            Article(
                source_name=source.name,
                title="Local date story",
                url="https://example.com/local-date-story",
                published_at=datetime(2026, 5, 22, 16, 45, tzinfo=timezone.utc),
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
            "2026-05-23T00:30:00+08:00",
        ]
    )

    assert code == 0
    assert (output_dir / "2026-05-23.md").exists()
    assert not (output_dir / "2026-05-22.md").exists()


def test_cli_invalid_now_exits_with_usage_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(
        cli,
        "fetch_source_articles",
        lambda source: pytest.fail("fetch_source_articles must not be called with an invalid --now"),
    )

    with pytest.raises(SystemExit) as exc:
        cli.main(
            [
                "run",
                "--config",
                str(config_path),
                "--output-dir",
                str(tmp_path / "out"),
                "--now",
                "not-a-timestamp",
            ]
        )

    assert exc.value.code == 2


@pytest.mark.parametrize("window_hours", ["0", "-1"])
def test_cli_rejects_nonpositive_window_hours(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, window_hours: str
) -> None:
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
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(
        cli,
        "fetch_source_articles",
        lambda source: pytest.fail("fetch_source_articles must not be called with nonpositive --window-hours"),
    )

    with pytest.raises(SystemExit) as exc:
        cli.main(["run", "--config", str(config_path), "--window-hours", window_hours])

    assert exc.value.code == 2
