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

    for source_name, summaries in _group_by_source(report.article_summaries).items():
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
