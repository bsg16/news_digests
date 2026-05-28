from datetime import datetime, timezone

import pytest

from news_digest.models import Article, ArticleSummary, TopicSummary
from news_digest.topics import build_topic_summaries


def article(source_name: str, title: str) -> Article:
    return Article(
        source_name=source_name,
        title=title,
        url=f"https://example.com/{source_name}/{abs(hash(title))}",
        published_at=datetime(2026, 5, 28, 8, 0, tzinfo=timezone.utc),
        author=None,
        source_text=f"{title} summary",
    )


def summary(source_name: str, title: str, tags: list[str] | None = None) -> ArticleSummary:
    return ArticleSummary(
        article=article(source_name, title),
        core_viewpoint=f"{title} 的核心观点。",
        key_points=[f"{title} 的关键信息。"],
        tags=tags or ["国际"],
    )


class FakeTopicMerger:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def merge_topic_summaries(self, candidates: list[TopicSummary]) -> list[TopicSummary]:
        self.calls.append([candidate.title for candidate in candidates])
        iran_candidates = [candidate for candidate in candidates if "Iran" in candidate.title]
        other_candidates = [candidate for candidate in candidates if "Iran" not in candidate.title]
        if len(iran_candidates) < 2:
            return candidates
        merged_articles = [
            article_summary
            for candidate in iran_candidates
            for article_summary in candidate.article_summaries
        ]
        merged = TopicSummary(
            title="美国对伊朗发动新一轮打击",
            core_viewpoint="美国对伊朗军事目标发动新一轮打击。",
            key_points=["美国发动军事打击。", "多家媒体报道同一事件。"],
            tags=["美国", "伊朗"],
            article_summaries=merged_articles,
        )
        return [merged, *other_candidates]


def test_build_topic_summaries_uses_chunked_llm_merge_then_final_reduce() -> None:
    summaries = [
        summary("BBC World", "US carries out new strikes on Iran military site"),
        summary("BBC World", "Five people found alive after week trapped in flooded Laos cave"),
        summary("Wall Street Journal World News", "U.S. Military Conducts New Strikes on Iran"),
        summary("BBC World", "Jill Biden says she thought husband was having a stroke during 2024 debate"),
    ]
    merger = FakeTopicMerger()

    topics = build_topic_summaries(summaries, merger, chunk_size=2, max_passes=2)

    assert len(topics) == 3
    assert topics[0].title == "美国对伊朗发动新一轮打击"
    assert [item.article.source_name for item in topics[0].article_summaries] == [
        "BBC World",
        "Wall Street Journal World News",
    ]
    assert merger.calls == [
        [
            "US carries out new strikes on Iran military site",
            "Five people found alive after week trapped in flooded Laos cave",
        ],
        [
            "U.S. Military Conducts New Strikes on Iran",
            "Jill Biden says she thought husband was having a stroke during 2024 debate",
        ],
        [
            "US carries out new strikes on Iran military site",
            "U.S. Military Conducts New Strikes on Iran",
        ],
        [
            "Five people found alive after week trapped in flooded Laos cave",
            "Jill Biden says she thought husband was having a stroke during 2024 debate",
        ],
    ]


def test_build_topic_summaries_passes_promotional_items_to_llm_instead_of_rule_filtering() -> None:
    promotional = summary("CNN World", "0% intro APR until 2024 is 100% insane")
    real_story = summary("BBC World", "US carries out new strikes on Iran military site")
    merger = FakeTopicMerger()

    build_topic_summaries([promotional, real_story], merger, chunk_size=10)

    assert merger.calls == [["0% intro APR until 2024 is 100% insane", "US carries out new strikes on Iran military site"]]


def test_build_topic_summaries_falls_back_to_singletons_when_llm_merge_fails() -> None:
    class FailingMerger:
        def merge_topic_summaries(self, candidates: list[TopicSummary]) -> list[TopicSummary]:
            raise RuntimeError("model unavailable")

    first = summary("BBC World", "Story one")
    second = summary("BBC World", "Story two")

    topics = build_topic_summaries([first, second], FailingMerger())

    assert [topic.title for topic in topics] == ["Story one", "Story two"]


def test_build_topic_summaries_rejects_nonpositive_chunk_size() -> None:
    with pytest.raises(ValueError, match="chunk_size"):
        build_topic_summaries([], FakeTopicMerger(), chunk_size=0)


def test_build_topic_summaries_never_sends_oversized_final_batch_to_llm() -> None:
    class RecordingMerger:
        def __init__(self) -> None:
            self.call_sizes: list[int] = []

        def merge_topic_summaries(self, candidates: list[TopicSummary]) -> list[TopicSummary]:
            self.call_sizes.append(len(candidates))
            return candidates

    merger = RecordingMerger()
    summaries = [summary("Example", f"Story {index}") for index in range(25)]

    build_topic_summaries(summaries, merger, chunk_size=10)

    assert merger.call_sizes
    assert max(merger.call_sizes) <= 10
