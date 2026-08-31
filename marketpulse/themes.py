"""Load the frozen 11-theme YAML. Membership is product-specific."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Theme:
    theme_id: str
    name: str
    members: tuple[str, ...]


@dataclass(frozen=True)
class ThemeSet:
    classification_version: str
    taxonomy_frozen_at: str
    notes: str
    themes: tuple[Theme, ...]

    def ids(self) -> list[str]:
        return [t.theme_id for t in self.themes]

    def by_id(self) -> dict[str, Theme]:
        return {t.theme_id: t for t in self.themes}

    def members_of(self, theme_id: str) -> tuple[str, ...]:
        return self.by_id()[theme_id].members


def load_themes(path: Path) -> ThemeSet:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw_themes = payload.get("themes") or {}
    if not isinstance(raw_themes, dict):
        raise ValueError("themes/v1.yaml must map theme_id -> {name, members}")
    themes: list[Theme] = []
    for theme_id, body in raw_themes.items():
        members = tuple(str(m) for m in (body.get("members") or []))
        if len(members) != len(set(members)):
            raise ValueError(f"duplicate members in {theme_id}")
        themes.append(
            Theme(
                theme_id=str(theme_id),
                name=str(body.get("name") or theme_id),
                members=members,
            )
        )
    if len(themes) != 11:
        raise ValueError(f"expected 11 themes, found {len(themes)}")
    return ThemeSet(
        classification_version=str(payload.get("classification_version") or ""),
        taxonomy_frozen_at=str(payload.get("taxonomy_frozen_at") or ""),
        notes=str(payload.get("notes") or "").strip(),
        themes=tuple(themes),
    )
