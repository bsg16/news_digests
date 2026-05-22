# News Digest Design

## Goal

Build a Python CLI that can run from cron every day, fetch articles from multiple configured news sources, summarize them in Chinese with an AI provider, and write a Markdown daily report.

The first implementation targets RSS/Atom sources. The configuration and code boundaries should leave room for future webpage sources and non-OpenAI AI providers without rewriting the pipeline.

## Confirmed Decisions

- Runtime shape: Python CLI run locally or on a server, suitable for cron.
- Source strategy: RSS/Atom first, with a future `webpage` source type reserved in the design.
- Source configuration: user-maintained `sources.yaml`.
- AI strategy: pluggable summarizer interface, default provider is DeepSeek.
- Output path: `output/YYYY-MM-DD.md`.
- Report time window: articles published in the past 24 hours from runtime.
- Report structure: global key points first, then article summaries grouped by source.
- Per-article summary language and format: Simplified Chinese, with a core viewpoint, an indented key-information bullet list, and tags.

## Architecture

Use a small modular CLI instead of a single large script.

- `cli`: parses command-line options, loads config, orchestrates the pipeline.
- `config`: reads and validates `sources.yaml` and runtime settings.
- `sources`: fetches and normalizes articles from configured sources.
- `summarizers`: defines the AI provider interface and the default DeepSeek implementation.
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

- `DEEPSEEK_API_KEY`
- `NEWS_DIGEST_MODEL`, optional model override

The default model should be `deepseek-v4-flash`, defined in code as a single constant so it can be changed safely later. This choice follows the requested default and favors a fast model for routine summarization while allowing `NEWS_DIGEST_MODEL` to override it.

The DeepSeek implementation should use DeepSeek's OpenAI-compatible Chat Completions API through the official Python OpenAI SDK, with `base_url` set to `https://api.deepseek.com`.

API keys must not be committed. Developers should set `DEEPSEEK_API_KEY` in the shell environment or an untracked local `.env` file.

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
6. Summarizer creates a concise Simplified Chinese summary for each article, including:
   - core viewpoint
   - key-information bullet list
   - tags
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

### 总统保留其他多项权力以征收进口税

- **核心观点**：尽管最高法院否决了特朗普总统通过《国际紧急经济权力法》(IEEPA)征收关税的权力，但他仍计划援引其他贸易法规继续征收进口关税，尽管这些替代方案可能限制更大且灵活性较低。
- **关键信息**：
    - 特朗普宣布将使用《1974年贸易法》第122条征收10%的全球关税，该条款此前从未被总统援引，且设150天期限。
    - 他还将利用《贸易扩张法》第232条对国家安全构成威胁的特定产品征收关税，以及《1974年贸易法》第301条调查不公平贸易行为并可能征收额外关税。
    - 这些替代权力在实施速度和灵活性上不如被最高法院否决的IEEPA。
    - 新的关税举措也可能面临法律挑战。
- **标签**：关税、美国政治、国际贸易
- 链接：https://example.com/article
- 发布时间：2026-05-22 08:15
```

The nested key-information list must use four spaces before each child bullet so the Markdown structure remains stable across renderers.

If no articles are found, still generate a report with a short "no articles in the selected window" message.

## Error Handling

The CLI should continue when one source fails and include a warning in logs. A single broken RSS feed should not block the entire digest.

Failure behavior:

- Missing `sources.yaml`: fail fast with a clear path-specific message.
- Invalid YAML or schema: fail fast and list the invalid field.
- Source network failure: log warning and continue other sources.
- Unsupported source type: fail config validation.
- Missing `DEEPSEEK_API_KEY` when using DeepSeek: fail before fetching sources.
- AI request failure for one article: mark that article as failed, continue the rest, and include enough log context to retry manually.
- Output write failure: fail the command.

## Testing Strategy

Use focused tests around pipeline boundaries:

- Config validation accepts valid RSS sources and rejects invalid source types.
- RSS parsing normalizes sample feeds into article objects.
- Time-window filtering keeps only articles from the past 24 hours.
- Deduplication removes duplicate URLs.
- Markdown rendering produces the expected sections and preserves four-space indentation for per-article key-information bullets.
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
