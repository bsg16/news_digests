from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
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

    try:
        now = parse_now(args.now)
    except ValueError as exc:
        parser.exit(2, f"config error: invalid --now timestamp: {exc}\n")

    model = os.getenv("NEWS_DIGEST_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    summarizer = build_summarizer(api_key, model)

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
    run.add_argument("--window-hours", type=positive_int, default=24)
    run.add_argument("--now", default=None, help="ISO timestamp for reproducible runs.")
    return parser


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def build_summarizer(api_key: str, model: str) -> DeepSeekSummarizer:
    return DeepSeekSummarizer(api_key=api_key, model=model)


def parse_now(value: str | None) -> datetime:
    if value is None:
        return datetime.now().astimezone()
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.astimezone()
    return parsed.astimezone()
