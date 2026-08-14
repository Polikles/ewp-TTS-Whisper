"""Release metadata and project licensing must remain synchronized."""

import tomllib
from pathlib import Path

from ewp_transcripts import __version__

ROOT = Path(__file__).resolve().parents[2]


def test_release_version_and_license_metadata() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert metadata["project"]["version"] == __version__
    assert metadata["project"]["license"] == "AGPL-3.0-or-later"
    assert metadata["project"]["license-files"] == ["LICENSE"]


def test_agpl_license_and_public_notice_are_present() -> None:
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert license_text.startswith("GNU AFFERO GENERAL PUBLIC LICENSE\nVersion 3")
    assert "END OF TERMS AND CONDITIONS" in license_text
    assert "AGPL-3.0-or-later" in readme
    assert "without warranty" in readme
