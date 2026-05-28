from __future__ import annotations

from typing import Protocol

from news_digest.models import ArticleSummary, TopicSummary


DEFAULT_TOPIC_CHUNK_SIZE = 30
DEFAULT_TOPIC_MERGE_PASSES = 3


class TopicMerger(Protocol):
    def merge_topic_summaries(self, candidates: list[TopicSummary]) -> list[TopicSummary]:
        raise NotImplementedError


def build_topic_summaries(
    article_summaries: list[ArticleSummary],
    topic_merger: TopicMerger,
    *,
    chunk_size: int = DEFAULT_TOPIC_CHUNK_SIZE,
    max_passes: int = DEFAULT_TOPIC_MERGE_PASSES,
) -> list[TopicSummary]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")
    if max_passes <= 0:
        raise ValueError("max_passes must be positive.")

    candidates = [_singleton_topic(summary) for summary in article_summaries]
    if not candidates:
        return []

    for pass_index in range(max_passes):
        if len(candidates) <= chunk_size:
            return _merge_or_keep(candidates, topic_merger)

        merged = _merge_in_chunks(candidates, topic_merger, chunk_size=chunk_size)
        if pass_index == max_passes - 1:
            return merged
        candidates = _interleave_for_next_pass(merged, chunk_size=chunk_size)

    return candidates


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


def _interleave_for_next_pass(candidates: list[TopicSummary], *, chunk_size: int) -> list[TopicSummary]:
    chunks = [candidates[index : index + chunk_size] for index in range(0, len(candidates), chunk_size)]
    interleaved: list[TopicSummary] = []
    for offset in range(chunk_size):
        for chunk in chunks:
            if offset < len(chunk):
                interleaved.append(chunk[offset])
    return interleaved


def _singleton_topic(summary: ArticleSummary) -> TopicSummary:
    return TopicSummary(
        title=summary.article.title,
        core_viewpoint=summary.core_viewpoint,
        key_points=summary.key_points,
        tags=summary.tags,
        article_summaries=[summary],
    )
