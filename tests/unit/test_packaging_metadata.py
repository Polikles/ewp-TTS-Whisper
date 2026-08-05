"""Release metadata must remain synchronized and exclude private draft material."""

import tomllib
from pathlib import Path

from ewp_transcripts import __version__

ROOT = Path(__file__).resolve().parents[2]


def test_release_version_and_private_license_exclusion() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert metadata["project"]["version"] == __version__
    assert metadata["project"]["license-files"] == []
    assert "LICENSE_SKETCH.TXT" in metadata["tool"]["hatch"]["build"]["exclude"]
