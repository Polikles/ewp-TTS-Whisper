"""Strict TOML configuration loading and precedence resolution."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from copy import deepcopy
from importlib.resources import files
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from ewp_transcripts.domain.enums import ChannelMode, LanguageMode
from ewp_transcripts.domain.errors import InvalidConfigurationError

ConfigurationData = dict[str, Any]


class StrictConfigModel(BaseModel):
    """Base model that rejects undocumented keys."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class GeneralConfig(StrictConfigModel):
    language: LanguageMode = LanguageMode.POLISH
    preset: Literal["accurate"] = "accurate"
    offline: bool = True
    interactive: bool = True


class InputConfig(StrictConfigModel):
    recursive: bool = False
    follow_symlinks: Literal[False] = False
    supported_audio: tuple[str, ...] = ("wav", "mp3", "flac", "m4a", "ogg", "opus")


class GroupingConfig(StrictConfigModel):
    speaker_suffix_separator: str = "-"
    parse_single_file_suffix_only_when_speaker_count_one: bool = True
    duration_warning_ms: int = Field(default=100, ge=0)
    duration_error_ms: int = Field(default=500, ge=0)
    require_equal_sample_rate: bool = True

    @model_validator(mode="after")
    def validate_duration_thresholds(self) -> GroupingConfig:
        if self.duration_error_ms < self.duration_warning_ms:
            raise ValueError("duration_error_ms must be at least duration_warning_ms")
        return self


class ChannelsConfig(StrictConfigModel):
    mode: ChannelMode = ChannelMode.AUTO
    ambiguous_fallback: ChannelMode = ChannelMode.DUAL_MONO
    dual_mono_min_correlation: float = Field(default=0.995, ge=0.0, le=1.0)
    dual_mono_max_rms_difference_db: float = Field(default=1.5, ge=0.0)
    dual_mono_max_normalized_difference: float = Field(default=0.1, ge=0.0)
    split_max_correlation: float = Field(default=0.5, ge=-1.0, le=1.0)
    split_min_each_exclusive_ratio: float = Field(default=0.05, ge=0.0, le=1.0)
    split_min_total_exclusive_ratio: float = Field(default=0.5, ge=0.0, le=1.0)
    mixed_min_both_active_ratio: float = Field(default=0.8, ge=0.0, le=1.0)
    mixed_min_normalized_difference: float = Field(default=0.1, ge=0.0)

    @model_validator(mode="after")
    def validate_channel_modes(self) -> ChannelsConfig:
        if self.mode is ChannelMode.AMBIGUOUS:
            raise ValueError("ambiguous is a detected mode and cannot be forced")
        if self.ambiguous_fallback is not ChannelMode.DUAL_MONO:
            raise ValueError("the MVP ambiguous fallback must use one channel")
        return self


class ModelsConfig(StrictConfigModel):
    asr_model: str = "large-v2"
    asr_repository: str = "Systran/faster-whisper-large-v2"
    asr_revision: str = "f0fe81560cb8b68660e564f55dd99207059c092e"
    asr_snapshot_path: Path = Path(
        "~/.cache/huggingface/hub/models--Systran--faster-whisper-large-v2/"
        "snapshots/f0fe81560cb8b68660e564f55dd99207059c092e"
    )
    alignment_model: str = "jonatasgrosman/wav2vec2-large-xlsr-53-polish"
    alignment_revision: str = "6b1cea36bd8bc5f65ec8081667cd9c0207d51970"
    alignment_snapshot_path: Path = Path(
        "~/.cache/huggingface/hub/"
        "models--jonatasgrosman--wav2vec2-large-xlsr-53-polish/"
        "snapshots/6b1cea36bd8bc5f65ec8081667cd9c0207d51970"
    )
    compute_type: Literal["float16"] = "float16"
    batch_size: int = Field(default=4, ge=1)
    device: Literal["cuda"] = "cuda"
    allow_network_downloads_during_transcription: bool = False

    @field_validator("asr_snapshot_path", "alignment_snapshot_path", mode="after")
    @classmethod
    def expand_snapshot_path(cls, value: Path) -> Path:
        return value.expanduser()

    @model_validator(mode="after")
    def validate_snapshot_revisions(self) -> ModelsConfig:
        snapshots = (
            ("asr_snapshot_path", self.asr_snapshot_path, self.asr_revision),
            (
                "alignment_snapshot_path",
                self.alignment_snapshot_path,
                self.alignment_revision,
            ),
        )
        for field_name, path, revision in snapshots:
            if path.name != revision:
                raise ValueError(f"{field_name} must end with its configured revision")
        return self


class DiarizationConfig(StrictConfigModel):
    model: str = "pyannote/speaker-diarization-community-1"
    local_model_path: Path = Path("~/.cache/ewp-transcripts/models/pyannote-community-1")
    speaker_count: Literal["auto"] | int = "auto"
    preserve_overlap: bool = True
    use_exclusive_for_word_assignment: bool = True

    @field_validator("speaker_count", mode="after")
    @classmethod
    def validate_speaker_count(cls, value: Literal["auto"] | int) -> Literal["auto"] | int:
        if isinstance(value, int) and value < 1:
            raise ValueError("speaker_count must be 'auto' or a positive integer")
        return value

    @field_validator("local_model_path", mode="after")
    @classmethod
    def expand_local_model_path(cls, value: Path) -> Path:
        return value.expanduser()


class QualityConfig(StrictConfigModel):
    analyze: bool = True
    warn_only: Literal[True] = True
    detect_clipping: bool = True
    detect_low_level: bool = True
    detect_channel_imbalance: bool = True
    detect_silence_ratio: bool = True
    clipping_min_sample_ratio: float = Field(default=0.0001, ge=0.0, le=1.0)
    low_level_max_rms_dbfs: float = Field(default=-35.0, le=0.0)
    channel_imbalance_min_rms_difference_db: float = Field(default=6.0, ge=0.0)
    high_silence_min_ratio: float = Field(default=0.5, ge=0.0, le=1.0)


class SubtitlesConfig(StrictConfigModel):
    preset: Literal["youtube"] = "youtube"
    max_lines: int = Field(default=2, ge=1)
    target_chars_per_line: int = Field(default=42, ge=1)
    max_chars_per_line: int = Field(default=46, ge=1)
    min_duration_ms: int = Field(default=1000, ge=0)
    max_duration_ms: int = Field(default=7000, ge=0)
    target_chars_per_second: int = Field(default=17, ge=1)
    max_chars_per_second: int = Field(default=20, ge=1)
    min_gap_ms: int = Field(default=80, ge=0)
    max_merge_gap_ms: int = Field(default=300, ge=0)
    speaker_labels: Literal["on-change", "always", "never"] = "on-change"


class OutputsConfig(StrictConfigModel):
    generate_txt: bool = True
    generate_srt: bool = True
    generate_vtt: bool = True
    generate_segments_json: bool = False
    batch_output_directory_name: str = "output-ewp-transcripts"
    encoding: Literal["utf-8"] = "utf-8"


class RuntimeConfig(StrictConfigModel):
    work_root: Path = Path("~/.cache/ewp-transcripts/work")
    keep_temp_on_success: bool = False
    keep_temp_on_error: bool = True
    continue_batch_after_error: bool = True
    max_concurrent_gpu_jobs: Literal[1] = 1
    lock_timeout_seconds: int = Field(default=0, ge=0)
    log_format: Literal["text", "jsonl"] = "text"
    log_transcript_text: bool = False

    @field_validator("work_root", mode="after")
    @classmethod
    def expand_work_root(cls, value: Path) -> Path:
        return value.expanduser()


class ApplicationConfig(StrictConfigModel):
    """Resolved, validated MVP configuration."""

    config_version: Literal["1.0"] = "1.0"
    general: GeneralConfig = GeneralConfig()
    input: InputConfig = InputConfig()
    grouping: GroupingConfig = GroupingConfig()
    channels: ChannelsConfig = ChannelsConfig()
    models: ModelsConfig = ModelsConfig()
    diarization: DiarizationConfig = DiarizationConfig()
    quality: QualityConfig = QualityConfig()
    subtitles: SubtitlesConfig = SubtitlesConfig()
    outputs: OutputsConfig = OutputsConfig()
    runtime: RuntimeConfig = RuntimeConfig()


PRESETS: dict[str, ConfigurationData] = {
    "accurate": {
        "models": {
            "asr_model": "large-v2",
            "compute_type": "float16",
            "device": "cuda",
        },
        "quality": {"analyze": True, "warn_only": True},
    }
}


def _merge(base: ConfigurationData, override: Mapping[str, Any]) -> ConfigurationData:
    merged = deepcopy(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, Mapping):
            merged[key] = _merge(current, value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _read_toml(path: Path, *, required: bool) -> ConfigurationData:
    try:
        with path.open("rb") as source:
            return tomllib.load(source)
    except FileNotFoundError as error:
        if not required:
            return {}
        raise InvalidConfigurationError(f"Configuration file does not exist: {path}") from error
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise InvalidConfigurationError(f"Cannot read configuration file: {path}") from error


def _packaged_defaults() -> ConfigurationData:
    resource = files("ewp_transcripts.resources").joinpath("default-config.toml")
    try:
        return tomllib.loads(resource.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise InvalidConfigurationError("Packaged default configuration is invalid") from error


def load_config(
    *,
    explicit_path: Path | None = None,
    cwd: Path | None = None,
    home: Path | None = None,
    cli_overrides: Mapping[str, Any] | None = None,
) -> ApplicationConfig:
    """Load configuration using the documented lowest-to-highest precedence."""

    working_directory = Path.cwd() if cwd is None else cwd
    home_directory = Path.home() if home is None else home
    user_data = _read_toml(
        home_directory / ".config/ewp-transcripts/config.toml",
        required=False,
    )
    project_data = _read_toml(working_directory / "transcriber.toml", required=False)
    explicit_data = _read_toml(explicit_path, required=True) if explicit_path else {}
    override_data = dict(cli_overrides or {})

    selectors: ConfigurationData = {}
    for layer in (user_data, project_data, explicit_data, override_data):
        selectors = _merge(selectors, layer)
    preset_name = selectors.get("general", {}).get("preset", "accurate")
    preset_data = PRESETS.get(preset_name, {})

    resolved = _packaged_defaults()
    for layer in (preset_data, user_data, project_data, explicit_data, override_data):
        resolved = _merge(resolved, layer)

    try:
        return ApplicationConfig.model_validate(resolved)
    except ValidationError as error:
        raise InvalidConfigurationError("Configuration validation failed") from error
