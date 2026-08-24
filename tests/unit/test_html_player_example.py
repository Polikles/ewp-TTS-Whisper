"""Contract tests for the separate consuming HTML player example."""

from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/html-player"


class _ContractParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, dict(attrs)))


def test_mock_player_embeds_accessible_fragment_without_inline_enhancement() -> None:
    markup = (EXAMPLE / "index.html").read_text(encoding="utf-8")
    parser = _ContractParser()
    parser.feed(markup)

    assert any(tag == "audio" and attrs.get("controls") is None for tag, attrs in parser.tags)
    assert any(
        tag == "section" and attrs.get("class") == "ewp-transcript" for tag, attrs in parser.tags
    )
    assert any(
        tag == "button" and attrs.get("type") == "button" and "data-start-ms" in attrs
        for tag, attrs in parser.tags
    )
    assert not any(
        name == "style" or name.startswith("on") for _tag, attrs in parser.tags for name in attrs
    )


def test_mock_player_owns_accessible_visual_and_playback_enhancement() -> None:
    styles = (EXAMPLE / "styles.css").read_text(encoding="utf-8")
    script = (EXAMPLE / "player.js").read_text(encoding="utf-8")

    assert "prefers-color-scheme: dark" in styles
    assert "prefers-reduced-motion: reduce" in script
    assert ":focus-visible" in styles
    assert '[aria-current="true"]' in styles
    assert 'cue.addEventListener("click"' in script
    assert 'player.addEventListener("timeupdate"' in script
    assert "player.currentTime = Number(cue.dataset.startMs) / 1000" in script
    assert 'activeCue.setAttribute("aria-current", "true")' in script
    assert "scrollIntoView" in script
