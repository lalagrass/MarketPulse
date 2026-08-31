from __future__ import annotations

from pathlib import Path

from marketpulse.themes import load_themes


def test_v1_yaml_has_eleven_themes() -> None:
    path = Path("themes/v1.yaml")
    themes = load_themes(path)
    assert len(themes.themes) == 11
    assert themes.classification_version
    for theme in themes.themes:
        assert len(theme.members) >= 4
        assert all(isinstance(m, str) for m in theme.members)
    ids = themes.ids()
    assert len(ids) == len(set(ids))
    assert "foundry_advanced" in ids
    assert "2330" in themes.members_of("foundry_advanced")
