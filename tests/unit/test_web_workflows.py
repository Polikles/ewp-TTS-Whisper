from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ewp_transcripts.web_workflows import GuiWorkflowController


class StubResult(BaseModel):
    selected: str
    mode: str
    output_directory: str | None = None


def test_inspect_calls_injected_application_service_and_records_result(tmp_path: Path) -> None:
    media = tmp_path / "episode.wav"
    media.write_bytes(b"audio")
    calls: list[tuple[Path, dict[str, Any]]] = []

    def inspect(path: Path, **kwargs: Any) -> BaseModel:
        calls.append((path, kwargs))
        return StubResult(selected=str(path), mode="inspect")

    controller = GuiWorkflowController((tmp_path.resolve(),), inspect_service=inspect)
    operation = controller.run("inspect", {"path": str(media)})

    assert operation.status == "completed"
    assert operation.result == {
        "selected": str(media),
        "mode": "inspect",
        "output_directory": None,
    }
    assert calls[0][0] == media
    assert "config" in calls[0][1]
    assert controller.operations() == (operation,)


def test_dry_run_passes_allowed_output_directory(tmp_path: Path) -> None:
    media = tmp_path / "episode.wav"
    media.write_bytes(b"audio")
    output = tmp_path / "exports"
    captured: dict[str, Any] = {}

    def plan(path: Path, **kwargs: Any) -> BaseModel:
        captured.update(kwargs)
        return StubResult(
            selected=str(path),
            mode="dry-run",
            output_directory=str(kwargs["output_directory"]),
        )

    controller = GuiWorkflowController((tmp_path.resolve(),), dry_run_service=plan)
    operation = controller.run("dry-run", {"path": str(media), "output_directory": str(output)})

    assert operation.status == "completed"
    assert captured["output_directory"] == output
    assert controller.has_completed_plan(media, output)
    assert not controller.has_completed_plan(media, tmp_path / "other")


def test_paths_outside_roots_and_symlinks_are_rejected(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.wav"
    outside.write_bytes(b"audio")
    link = allowed / "link.wav"
    link.symlink_to(outside)
    controller = GuiWorkflowController((allowed.resolve(),))

    outside_result = controller.run("inspect", {"path": str(outside)})
    link_result = controller.run("inspect", {"path": str(link)})

    assert outside_result.error is not None
    assert outside_result.error["code"] == "GUI_PATH_REJECTED"
    assert link_result.error is not None
    assert link_result.error["code"] == "GUI_PATH_REJECTED"


def test_missing_path_is_a_coded_failure(tmp_path: Path) -> None:
    controller = GuiWorkflowController((tmp_path.resolve(),))

    operation = controller.run("inspect", {})

    assert operation.status == "failed"
    assert operation.error == {
        "code": "GUI_REQUEST_INVALID",
        "message": "A non-empty path is required.",
    }
