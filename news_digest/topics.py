from __future__ import annotations

from typing import Protocol

from news_digest.models import ArticleSummary, TopicSummary


DEFAULT_TOPIC_CHUNK_SIZE = 30
DEFAULT_FINAL_TOPIC_CHUNK_SIZE = 200


class TopicMerger(Protocol):
    def merge_topic_summaries(self, candidates: list[TopicSummary]) -> list[TopicSummary]:
        raise NotImplementedError


def build_topic_summaries(
    article_summaries: list[ArticleSummary],
    topic_merger: TopicMerger,
    *,
    chunk_size: int = DEFAULT_TOPIC_CHUNK_SIZE,
    final_chunk_size: int = DEFAULT_FINAL_TOPIC_CHUNK_SIZE,
) -> list[TopicSummary]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")
    if final_chunk_size <= 0:
        raise ValueError("final_chunk_size must be positive.")

    candidates = [_singleton_topic(summary) for summary in article_summaries]
    if not candidates:
        return []

    if len(candidates) > chunk_size:
        candidates = _merge_in_chunks(candidates, topic_merger, chunk_size=chunk_size)

    if len(candidates) <= final_chunk_size:
        return _merge_or_keep(candidates, topic_merger)

    while len(candidates) > final_chunk_size:
        previous_count = len(candidates)
        candidates = _merge_in_chunks(candidates, topic_merger, chunk_size=chunk_size)
        if len(candidates) >= previous_count:
            return candidates

    return _merge_or_keep(candidates, topic_merger)


def _merge_in_chunks(
    candidates: list[TopicSummary],
    topic_merger: TopicMerger,
    *,
    chunk_size: int,
) -> list[TopicSummary]:
    merged: list[TopicSummary] = []
    for index in range(0, len(candidates), chunk_size):
        merged.extend(_merge_or_keep(candidates[index : index + chunk_size], topic_merger))
    return merged


def _merge_or_keep(candidates: list[TopicSummary], topic_merger: TopicMerger) -> list[TopicSummary]:
    try:
        merged = topic_merger.merge_topic_summaries(candidates)
    except Exception:
        return candidates
    return merged


def _singleton_topic(summary: ArticleSummary) -> TopicSummary:
    return TopicSummary(
        title=summary.article.title,
        core_viewpoint=summary.core_viewpoint,
        key_points=summary.key_points,
        tags=summary.tags,
        article_summaries=[summary],
    )
