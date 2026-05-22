from datetime import datetime, timezone

from news_digest.models import Article, ArticleSummary
from news_digest.summarizers.deepseek import DEFAULT_MODEL, DeepSeekSummarizer


class FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = FakeMessage(content)


class FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [FakeChoice(content)]


class FakeCompletions:
    def __init__(self) -> None:
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if "全局要点" in kwargs["messages"][1]["content"]:
            return FakeResponse('{"global_key_points":["第一条全局要点","第二条全局要点"]}')
        return FakeResponse(
            '{"core_viewpoint":"核心观点文本","key_points":["要点一","要点二"],"tags":["政治","贸易"]}'
        )


class FakeChat:
    def __init__(self) -> None:
        self.completions = FakeCompletions()


class FakeClient:
    def __init__(self) -> None:
        self.chat = FakeChat()


def sample_article() -> Article:
    return Article(
        source_name="BBC News",
        title="Trade story",
        url="https://example.com/trade",
        published_at=datetime(2026, 5, 22, 4, 0, tzinfo=timezone.utc),
        author=None,
        source_text="A story about trade policy.",
    )


def test_deepseek_summarizer_uses_default_model_and_parses_article_json() -> None:
    client = FakeClient()
    summarizer = DeepSeekSummarizer(api_key="test-key", client=client)

    result = summarizer.summarize_article(sample_article())

    assert DEFAULT_MODEL == "deepseek-v4-flash"
    assert result.core_viewpoint == "核心观点文本"
    assert result.key_points == ["要点一", "要点二"]
    assert result.tags == ["政治", "贸易"]
    call = client.chat.completions.calls[0]
    assert call["model"] == "deepseek-v4-flash"
    assert call["response_format"] == {"type": "json_object"}


def test_deepseek_summarizer_parses_global_key_points() -> None:
    client = FakeClient()
    summarizer = DeepSeekSummarizer(api_key="test-key", client=client)
    article_summary = ArticleSummary(
        article=sample_article(),
        core_viewpoint="核心观点文本",
        key_points=["要点一"],
        tags=["政治"],
    )

    result = summarizer.summarize_global_key_points([article_summary])

    assert result == ["第一条全局要点", "第二条全局要点"]
