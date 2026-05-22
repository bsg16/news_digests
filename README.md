# News Digest

Fetch RSS articles from configured news sources, summarize them in Simplified Chinese with DeepSeek, and write a Markdown daily report to `output/YYYY-MM-DD.md`.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp sources.yaml.example sources.yaml
cp .env.example .env
```

Edit `.env` and set `DEEPSEEK_API_KEY`.

## Run

```bash
news-digest run
```

Equivalent module command:

```bash
python -m news_digest run
```

## Configuration

RSS sources live in `sources.yaml`. The provided `sources.yaml.example` includes starter feeds for BBC, CNN, New York Times, The Economist, Wall Street Journal, and a disabled Global Times candidate.

The Global Times candidate is disabled because the accessible RSS feed is titled `outbrain` and may not provide stable daily coverage. The Economist and Wall Street Journal feeds may contain only RSS summaries or links to paywalled articles; this tool summarizes only feed text that is available in RSS.

## Environment

- `DEEPSEEK_API_KEY`: required.
- `NEWS_DIGEST_MODEL`: optional, defaults to `deepseek-v4-flash`.

## Cron Example

Run every day at 08:00 server time:

```cron
0 8 * * * cd /Users/fangqian/deploy/news_digests && /Users/fangqian/deploy/news_digests/.venv/bin/news-digest run >> /Users/fangqian/deploy/news_digests/news-digest.log 2>&1
```

## Test

```bash
.venv/bin/python -m pytest
```
