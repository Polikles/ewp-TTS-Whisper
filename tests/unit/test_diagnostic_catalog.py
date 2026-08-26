"""Keep stable user-visible diagnostic codes documented and machine-checkable."""

import inspect
import re
from pathlib import Path

from ewp_transcripts.domain.enums import WarningCode
from ewp_transcripts.domain.errors import ApplicationError

CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]+$")


def _error_types(root: type[ApplicationError]) -> set[type[ApplicationError]]:
    found: set[type[ApplicationError]] = set()
    pending = list(root.__subclasses__())
    while pending:
        error_type = pending.pop()
        if error_type in found:
            continue
        found.add(error_type)
        pending.extend(error_type.__subclasses__())
    return found


def test_every_expected_application_error_has_a_stable_code() -> None:
    for error_type in _error_types(ApplicationError) | {ApplicationError}:
        code = getattr(error_type, "code", None)
        assert isinstance(code, str), error_type.__name__
        assert CODE_PATTERN.fullmatch(code), (error_type.__name__, code)


def test_catalog_contains_codes_emitted_by_current_implementation() -> None:
    root = Path(__file__).parents[2]
    catalog = (root / "docs" / "25-warning-error-catalog.md").read_text(encoding="utf-8")
    codes = {item.value for item in WarningCode}
    codes.update(error_type.code for error_type in _error_types(ApplicationError))
    codes.add(ApplicationError.code)

    sources = (
        root / "src" / "ewp_transcripts" / "cli.py",
        root / "src" / "ewp_transcripts" / "application.py",
        root / "src" / "ewp_transcripts" / "review_format.py",
        root / "src" / "ewp_transcripts" / "revision_service.py",
        root / "src" / "ewp_transcripts" / "translation_lm_studio.py",
    )
    for source in sources:
        text = inspect.cleandoc(source.read_text(encoding="utf-8"))
        codes.update(re.findall(r'fallback_code="([A-Z][A-Z0-9_]+)"', text))
        codes.update(re.findall(r'_coded_warning\(\s*"([A-Z][A-Z0-9_]+)"', text))
        codes.update(re.findall(r'"(CLI_[A-Z0-9_]+):', text))
        codes.update(re.findall(r'(?:code|failure_code)="([A-Z][A-Z0-9_]+)"', text))
        codes.update(re.findall(r'"(PROVIDER_[A-Z0-9_]+)"', text))

    missing = sorted(code for code in codes if f"`{code}`" not in catalog)
    assert missing == []
