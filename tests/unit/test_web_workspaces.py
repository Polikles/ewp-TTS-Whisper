from pathlib import Path

import pytest

from ewp_transcripts.web_workflows import GuiWorkflowController
from ewp_transcripts.web_workspaces import GuiWorkspaceController


def controller(tmp_path: Path) -> tuple[GuiWorkspaceController, Path]:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    workflows = GuiWorkflowController((allowed.resolve(),))
    return (
        GuiWorkspaceController(
            state_directory=tmp_path / "state",
            resolve_path=workflows.resolve_allowed_path,
        ),
        allowed,
    )


def test_workspace_round_trip_contains_only_allowlisted_non_secret_fields(tmp_path: Path) -> None:
    workspaces, allowed = controller(tmp_path)
    media = allowed / "episode.wav"
    media.write_bytes(b"audio")

    saved = workspaces.save(
        name="Episode work",
        current_step="correction-heading",
        fields={
            "input-path": str(media),
            "output-path": str(allowed / "output"),
            "workflow-language": "pl",
            "workflow-speaker-auto": True,
        },
    )
    loaded = workspaces.load(saved.workspace_id)
    listed = workspaces.list()

    assert loaded == saved
    assert loaded.fields["input-path"] == str(media)
    assert listed[0].workspace_id == saved.workspace_id
    assert listed[0].available is True
    assert (tmp_path / "state" / f"{saved.workspace_id}.json").stat().st_mode & 0o777 == 0o600


def test_workspace_rejects_unknown_fields_and_outside_paths(tmp_path: Path) -> None:
    workspaces, _ = controller(tmp_path)

    with pytest.raises(ValueError, match="unsupported field"):
        workspaces.save(name="Bad", current_step="", fields={"api_key": "secret"})
    outside = tmp_path / "outside.wav"
    outside.write_bytes(b"audio")
    with pytest.raises(ValueError, match="outside"):
        workspaces.save(
            name="Bad path",
            current_step="",
            fields={"input-path": str(outside)},
        )


def test_missing_saved_path_marks_summary_unavailable(tmp_path: Path) -> None:
    workspaces, allowed = controller(tmp_path)
    media = allowed / "episode.wav"
    media.write_bytes(b"audio")
    saved = workspaces.save(
        name="Temporary",
        current_step="workspace-heading",
        fields={"input-path": str(media)},
    )
    media.unlink()

    assert workspaces.list()[0].available is False
    with pytest.raises(FileNotFoundError):
        workspaces.load(saved.workspace_id)
