# News Digest

从多个 RSS 新闻源抓取文章，使用 DeepSeek 生成简体中文摘要，并输出 Markdown 新闻日报。

当前版本默认生成“主题日报”：先对文章做单篇摘要，再让 LLM 分块执行语义去重、主题合并和低价值条目剔除，最后输出按新闻主题整理的 Markdown。

## 功能

- 多 RSS 源抓取：BBC、CNN、纽约时报、经济学人、华尔街日报等。
- 24 小时窗口过滤：默认只处理过去 24 小时内的文章。
- URL 硬去重：去掉完全重复或带追踪参数的重复链接。
- AI 中文摘要：每篇文章先生成核心观点、关键信息、标签。
- LLM 分块去重：不依赖标题关键词规则，由 LLM 判断同一事件、合并主题、剔除广告或低价值条目。
- Markdown 日报输出：默认写入 `output/YYYY-MM-DD.md`。
- 容错处理：单个 RSS 源或单篇摘要失败不会中断整轮日报。

## 工作流

```text
RSS 抓取
→ 时间窗口过滤
→ URL 去重
→ 单篇 AI 摘要
→ 候选主题构建
→ LLM 分块主题合并/剔除
→ 全局要点生成
→ Markdown 日报
```

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp sources.yaml.example sources.yaml
cp .env.example .env
```

编辑 `.env`：

```env
DEEPSEEK_API_KEY=你的 DeepSeek API Key
NEWS_DIGEST_MODEL=deepseek-v4-flash
```

不要把 `.env` 提交到 Git。仓库已通过 `.gitignore` 忽略 `.env`、`output/`、虚拟环境和日志文件。

## 配置新闻源

RSS 源配置在 `sources.yaml`：

```yaml
sources:
  - name: BBC News
    type: rss
    url: http://feeds.bbci.co.uk/news/rss.xml
    enabled: true
    language: en
```

字段说明：

- `name`：新闻源名称，会出现在日报来源中。
- `type`：当前支持 `rss`。
- `url`：RSS 地址。
- `enabled`：是否启用。
- `language`：源语言标记，当前主要作为配置说明保留。

`sources.yaml.example` 已包含 BBC、CNN、纽约时报、经济学人、华尔街日报，以及一个默认禁用的环球时报候选源。

## 运行

默认运行：

```bash
news-digest run
```

等价模块命令：

```bash
python -m news_digest run
```

指定配置、输出目录和时间窗口：

```bash
news-digest run \
  --config sources.yaml \
  --output-dir output \
  --window-hours 24
```

指定生成时间，便于复现或测试：

```bash
news-digest run --now "2026-05-28T08:00:00+08:00"
```

## 输出格式

日报示例：

```markdown
# 新闻日报 - 2026-05-28

生成时间：2026-05-28 08:00 CST
范围：过去 24 小时

## 全局要点

- ...

## 新闻主题

### 美国再次打击伊朗军事目标

- **核心观点**：美国对伊朗军事设施发动新一轮打击，美伊紧张局势继续升级。
- **关键信息**：
    - 美国实施军事打击。
    - 多家媒体报道同一事件。
    - 中东安全风险上升。
- **标签**：美国、伊朗、军事冲突
- **来源**：BBC World、Wall Street Journal World News
- **相关链接**：
    - BBC World｜标题：https://example.com/article
    - Wall Street Journal World News｜标题：https://example.com/article
```

## 定时任务

每天早上 8 点运行：

```cron
0 8 * * * cd /Users/fangqian/deploy/news_digests && /Users/fangqian/deploy/news_digests/.venv/bin/news-digest run >> /Users/fangqian/deploy/news_digests/news-digest.log 2>&1
```

如部署到服务器，请把路径替换成服务器上的项目路径。

## 测试

```bash
.venv/bin/python -m pytest -q
```

当前测试覆盖：

- RSS 解析和时间过滤
- URL 去重
- DeepSeek JSON 解析和错误处理
- LLM 分块主题合并
- Markdown 渲染
- CLI 参数和输出路径

## 安全说明

- API key 只应放在 `.env` 或系统凭据管理器中。
- 不要把 token 写进 Git remote URL。
- `output/` 默认不提交，避免把每天生成的日报和潜在敏感运行结果放入仓库。
- 如果 API key 或 GitHub token 曾出现在聊天或终端历史中，建议在服务商后台按需轮换。

## GitHub

当前远端仓库：

```text
https://github.com/bsg16/news_digests
```

常用命令：

```bash
git status
git add .
git commit -m "Describe your change"
git push
```
