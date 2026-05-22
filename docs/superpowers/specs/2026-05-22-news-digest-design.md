# News Digest Design

## Goal

Build a Python CLI that can run from cron every day, fetch articles from multiple configured news sources, summarize them in Chinese with an AI provider, and write a Markdown daily report.

The first implementation targets RSS/Atom sources. The configuration and code boundaries should leave room for future webpage sources and non-OpenAI AI providers without rewriting the pipeline.

## Confirmed Decisions

- Runtime shape: Python CLI run locally or on a server, suitable for cron.
- Source strategy: RSS/Atom first, with a future `webpage` source type reserved in the design.
- Source configuration: user-maintained `sources.yaml`.
- AI strategy: pluggable summarizer interface, default provider is OpenAI.
- Output path: `output/YYYY-MM-DD.md`.
- Report time window: articles published in the past 24 hours from runtime.
- Report structure: global key points first, then article summaries grouped by source.

## Architecture

Use a small modular CLI instead of a single large script.

- `cli`: parses command-line options, loads config, orchestrates the pipeline.
- `config`: reads and validates `sources.yaml` and runtime settings.
- `sources`: fetches and normalizes articles from configured sources.
- `summarizers`: defines the AI provider interface and the default OpenAI implementation.
- `renderer`: turns normalized summaries into Markdown.
- `models`: shared dataclasses for sources, articles, summaries, and report metadata.

The CLI should be usable with a default command:

```bash
python -m news_digest run
```

Optional arguments can override the config path, output directory, time window, and dry-run behavior.

## Configuration

`sources.yaml` owns the news source list. First version supports `rss` entries:

```yaml
sources:
  - name: Example News
    type: rss
    url: https://example.com/feed.xml
    enabled: true
    language: en
```

Reserved future shape for webpage sources:

```yaml
sources:
  - name: Example Site
    type: webpage
    url: https://example.com/news
    enabled: true
```

The first implementation should reject unsupported source types with a clear error instead of silently ignoring them.

AI settings should come from environment variables by default:

- `OPENAI_API_KEY`
- `NEWS_DIGEST_MODEL`, optional model override

The default model should be `gpt-5.4-mini`, defined in code as a single constant so it can be changed safely later. This choice favors lower latency and cost for routine summarization while allowing `NEWS_DIGEST_MODEL` to override it.

The OpenAI implementation should use the Responses API through the official Python SDK.

## Data Flow

1. CLI loads `sources.yaml`.
2. Config validation filters disabled sources and reports invalid entries.
3. RSS fetcher downloads feeds and normalizes entries into articles with:
   - source name
   - title
   - URL
   - published timestamp when available
   - author when available
   - short source text from feed summary/content
4. Pipeline filters articles to the past 24 hours.
5. Pipeline deduplicates articles by canonical URL, falling back to title plus source when URL is missing.
6. Summarizer creates a concise Chinese summary for each article.
7. Summarizer creates global key points from the day article summaries.
8. Renderer writes `output/YYYY-MM-DD.md`.

## Markdown Output

The report should be readable in plain Markdown:

```markdown
# 新闻日报 - 2026-05-22

生成时间：2026-05-22 19:30 Asia/Shanghai
范围：过去 24 小时

## 全局要点

- ...

## Example News

### Article Title

- 摘要：...
- 链接：https://example.com/article
- 发布时间：2026-05-22 08:15
```

If no articles are found, still generate a report with a short "no articles in the selected window" message.

## Error Handling

The CLI should continue when one source fails and include a warning in logs. A single broken RSS feed should not block the entire digest.

Failure behavior:

- Missing `sources.yaml`: fail fast with a clear path-specific message.
- Invalid YAML or schema: fail fast and list the invalid field.
- Source network failure: log warning and continue other sources.
- Unsupported source type: fail config validation.
- Missing `OPENAI_API_KEY` when using OpenAI: fail before fetching sources.
- AI request failure for one article: mark that article as failed, continue the rest, and include enough log context to retry manually.
- Output write failure: fail the command.

## Testing Strategy

Use focused tests around pipeline boundaries:

- Config validation accepts valid RSS sources and rejects invalid source types.
- RSS parsing normalizes sample feeds into article objects.
- Time-window filtering keeps only articles from the past 24 hours.
- Deduplication removes duplicate URLs.
- Markdown rendering produces the expected sections.
- Summarizer interface can be tested with a fake provider to avoid network calls.

Integration-level verification should run the CLI against a sample local feed fixture and a fake summarizer.

## Non-Goals For First Version

- Web UI.
- Database-backed history.
- Automatic discovery of news sources.
- Full webpage scraping implementation.
- Automatic Git commit or publishing.
- Multi-language report output.

## Implementation Notes

- Cron setup can be documented after the CLI command and config path are stable.
