from datetime import datetime, timezone
from pathlib import Path

from news_digest.models import Article, ArticleSummary, DigestReport, SourceError, TopicSummary
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


def test_render_markdown_renders_failed_article_summary_in_normal_article_format() -> None:
    failed = ArticleSummary(
        article=Article(
            source_name="Example",
            title="Story with failed summary",
            url="https://example.com/failed",
            published_at=datetime(2026, 5, 22, 8, 15, tzinfo=timezone.utc),
            author=None,
            source_text="source text",
        ),
        core_viewpoint="摘要生成失败。",
        key_points=["摘要生成失败：model unavailable"],
        tags=["摘要失败"],
        summary_error="model unavailable",
    )
    report = DigestReport(
        generated_at=datetime(2026, 5, 22, 19, 30, tzinfo=timezone.utc),
        window_hours=24,
        article_summaries=[failed],
        global_key_points=[],
    )

    markdown = render_markdown(report)

    assert "## Example" in markdown
    assert "### Story with failed summary" in markdown
    assert "- **核心观点**：摘要生成失败。" in markdown
    assert "- **关键信息**：\n    - 摘要生成失败：model unavailable" in markdown
    assert "- **标签**：摘要失败" in markdown


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


def test_render_markdown_empty_report_uses_report_window_hours() -> None:
    report = DigestReport(
        generated_at=datetime(2026, 5, 22, 19, 30, tzinfo=timezone.utc),
        window_hours=6,
        article_summaries=[],
    )

    markdown = render_markdown(report)

    assert "过去 6 小时内没有找到可摘要的文章。" in markdown
    assert "过去 24 小时内没有找到可摘要的文章。" not in markdown


def test_render_markdown_does_not_claim_no_articles_when_only_global_points_are_missing() -> None:
    report = DigestReport(
        generated_at=datetime(2026, 5, 22, 19, 30, tzinfo=timezone.utc),
        window_hours=24,
        article_summaries=[summary("BBC News", "Story")],
        global_key_points=[],
    )

    markdown = render_markdown(report)

    assert "没有找到可摘要的文章" not in markdown
    assert "## BBC News" in markdown
    assert "### Story" in markdown


def test_render_markdown_empty_report_shows_no_articles_even_with_global_points() -> None:
    report = DigestReport(
        generated_at=datetime(2026, 5, 22, 19, 30, tzinfo=timezone.utc),
        window_hours=6,
        article_summaries=[],
        global_key_points=["摘要器返回了全局要点。"],
    )

    markdown = render_markdown(report)

    assert "## 全局要点\n\n- 过去 6 小时内没有找到可摘要的文章。" in markdown
    assert "摘要器返回了全局要点。" not in markdown


def test_render_markdown_groups_articles_by_first_seen_source_order() -> None:
    report = DigestReport(
        generated_at=datetime(2026, 5, 22, 19, 30, tzinfo=timezone.utc),
        window_hours=24,
        article_summaries=[
            summary("BBC News", "BBC first"),
            summary("Reuters", "Reuters story"),
            summary("BBC News", "BBC second"),
        ],
        global_key_points=["全球新闻摘要。"],
    )

    markdown = render_markdown(report)

    bbc_index = markdown.index("## BBC News")
    reuters_index = markdown.index("## Reuters")
    assert bbc_index < reuters_index
    bbc_section = markdown[bbc_index:reuters_index]
    assert "### BBC first" in bbc_section
    assert "### BBC second" in bbc_section
    assert "### Reuters story" not in bbc_section


def test_render_markdown_uses_topic_summaries_when_present() -> None:
    first = summary("BBC World", "US carries out new strikes on Iran military site")
    second = summary("Wall Street Journal World News", "U.S. Military Conducts New Strikes on Iran")
    report = DigestReport(
        generated_at=datetime(2026, 5, 22, 19, 30, tzinfo=timezone.utc),
        window_hours=24,
        article_summaries=[first, second],
        topic_summaries=[
            TopicSummary(
                title="US carries out new strikes on Iran military site",
                core_viewpoint="美国对伊朗军事设施发动新一轮打击。",
                key_points=["美国发动军事打击。", "多家媒体报道同一事件。"],
                tags=["美国", "伊朗"],
                article_summaries=[first, second],
            )
        ],
        global_key_points=["美伊局势紧张。"],
    )

    markdown = render_markdown(report)

    assert "## 新闻主题" in markdown
    assert "## BBC World" not in markdown
    assert "### US carries out new strikes on Iran military site" in markdown
    assert "- **来源**：BBC World、Wall Street Journal World News" in markdown
    assert "- **相关链接**：" in markdown
    assert "    - BBC World｜US carries out new strikes on Iran military site：https://example.com/article" in markdown


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
