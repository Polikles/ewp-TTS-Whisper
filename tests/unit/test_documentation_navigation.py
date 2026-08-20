"""Keep live documentation navigable and historical runbooks out of the operator set."""

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
MARKDOWN_LINK = re.compile(r"\[[^]]*\]\(([^)]+)\)")


def test_live_local_markdown_links_resolve() -> None:
    documents = (
        tuple(ROOT.glob("*.md"))
        + tuple((ROOT / "docs").rglob("*.md"))
        + tuple((ROOT / "WSL config").rglob("*.md"))
    )
    missing: list[str] = []
    for document in documents:
        for raw_target in MARKDOWN_LINK.findall(document.read_text(encoding="utf-8")):
            target = raw_target.split("#", maxsplit=1)[0]
            if not target or "://" in target or target.startswith("mailto:") or "<" in target:
                continue
            resolved = (document.parent / unquote(target)).resolve()
            if not resolved.exists():
                missing.append(f"{document.relative_to(ROOT)} -> {raw_target}")

    assert missing == []


def test_live_operator_directory_contains_only_current_runbook() -> None:
    operator_root = ROOT / "WSL config"

    assert {path.name for path in operator_root.glob("RUN_*.md")} == {
        "RUN_RELEASE_FRESH_WSL_INSTALL.md",
        "RUN_V03_LOCAL_LLM_BENCHMARK.md",
    }
    assert (operator_root / "USE_CURRENT_MVP.md").is_file()
    assert (operator_root / "FEEDBACK_FOR_V2.md").is_file()
