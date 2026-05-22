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
