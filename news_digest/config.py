from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from news_digest.models import SourceConfig


SUPPORTED_SOURCE_TYPES = {"rss"}


class ConfigError(ValueError):
    pass


def load_sources_config(path: Path) -> list[SourceConfig]:
    if not path.exists():
        raise ConfigError(f"Config file {path} does not exist. Copy sources.yaml.example to sources.yaml first.")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError("Config root must be a mapping with a sources list.")

    raw_sources = raw.get("sources")
    if not isinstance(raw_sources, list):
        raise ConfigError("Config field sources must be a list.")

    sources: list[SourceConfig] = []
    for index, item in enumerate(raw_sources, start=1):
        if not isinstance(item, dict):
            raise ConfigError(f"Source #{index} must be a mapping.")

        source = _parse_source(index, item)
        if source.enabled:
            sources.append(source)

    return sources


def _parse_source(index: int, item: dict[str, Any]) -> SourceConfig:
    name = _required_string(index, item, "name")
    source_type = _required_string(index, item, "type")
    url = _required_string(index, item, "url")
    enabled = item.get("enabled", True)
    language = item.get("language", "en")

    if source_type not in SUPPORTED_SOURCE_TYPES:
        raise ConfigError(f"Source #{index} has unsupported source type {source_type!r}. Supported types: rss.")
    if not isinstance(enabled, bool):
        raise ConfigError(f"Source #{index} field enabled must be true or false.")
    if not isinstance(language, str) or not language.strip():
        raise ConfigError(f"Source #{index} field language must be a non-empty string.")

    return SourceConfig(
        name=name,
        type=source_type,
        url=url,
        enabled=enabled,
        language=language.strip(),
    )


def _required_string(index: int, item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"Source #{index} field {key} must be a non-empty string.")
    return value.strip()
