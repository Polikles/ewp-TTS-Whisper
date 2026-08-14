# TOML Configuration

## 1. Precedence

From highest to lowest priority:

```text
> CLI flag
> file selected with --config
> project configuration
> user configuration
> preset
> application default
```

The effective configuration must be stored in `results.json`, excluding secrets.

## 2. Locations

Recommended locations:

```text
project: ./transcriber.toml (resolved from the command's current working directory)
user: ~/.config/ewp-transcripts/config.toml (applies from every working directory)
```

An arbitrary file may instead be selected with `--config /exact/path/to/file.toml`.
Configuration keys must be placed below their TOML section header; for example,
`editor` belongs below `[revision]`.

The application should not modify project configuration automatically.

## 3. Sections

Complete example: [`../examples/config.example.toml`](../examples/config.example.toml).

- `[general]` — language, preset, offline mode, interactivity;
- `[input]` — recursion, supported formats, symbolic links;
- `[grouping]` — speaker separator and duration thresholds;
- `[channels]` — classification mode and thresholds;
- `[models]` — models, cache paths, compute type, batch size;
- `[diarization]` — model, speaker count, overlap behavior;
- `[subtitles]` — cue rules;
- `[outputs]` — default exports and naming;
- `[runtime]` — work directories, temporary files, locks, logging;
- `[quality]` — diagnostics without audio repair.

### Warning-only quality thresholds

Inspection decodes each source once and reports four lightweight diagnostics. The MVP
defaults are deliberately conservative:

| Key | Default | Warning condition |
|---|---:|---|
| `clipping_min_sample_ratio` | `0.0001` | At least this fraction of decoded PCM samples is at or near full scale. |
| `low_level_max_rms_dbfs` | `-35.0` | The louder channel's overall RMS is at or below this level. |
| `channel_imbalance_min_rms_difference_db` | `6.0` | A true two-channel source differs by at least this RMS level. |
| `high_silence_min_ratio` | `0.5` | At least this fraction of 500 ms windows has neither channel active. |

Individual `detect_*` switches may disable a warning, and `analyze = false` disables all
four. Diagnostics never normalize, repair, or otherwise modify input audio. These
thresholds are an initial operational baseline and must be recalibrated on the future
larger dataset.

## 4. `accurate` preset

The MVP preset is optimized for an RTX 3090 and prioritizes quality. It should define:

- `large-v2` by default, selected through ADR-0007's initial project benchmark;
- CUDA `float16`;
- a batch size validated by an OOM stability test;
- word alignment;
- full diarization when required;
- no quality-reducing quantization;
- no automatic audio repair.

The ASR model and batch size must remain configurable.

Model selection is separate from local artifact resolution. The `[models]` and
`[diarization]` sections record, for ASR, Polish word alignment, and Community-1:

- the model or repository identifier;
- the exact immutable revision;
- the explicit local snapshot directory.

The snapshot path is authoritative at transcription time. EWP-transcripts does not
search an arbitrary Hugging Face cache, resolve a moving branch, or download a missing
artifact while transcribing. Each snapshot path must end with its configured revision;
existence and model compatibility are checked by the runtime operation that loads it.
The packaged paths assume the standard `~/.cache/huggingface` location established by
the WSL setup guide. Installations with a different `HF_HOME` must override all three paths.

The selection is provisional because the comparison corpus contained only three cases. A larger manually verified corpus may justify changing the default through a new or superseding ADR.

## 5. Validation

- unknown keys: error in strict mode, warning in compatibility mode;
- out-of-range values: error before models are loaded;
- CLI/TOML conflict: CLI wins and the override appears in debug logs;
- secrets are not allowed in project TOML.

## 6. Compatibility

Configuration should include an optional version:

```toml
config_version = "1.0"
```

Changing the meaning of an existing key requires a major configuration-version update or a migration layer.


## 7. Transcript revision configuration

Manual revision uses the normal precedence rules and adds a strict `[revision]` section.
The v0.2.0 defaults are:

```toml
[revision]
anchor_target_words = 200
long_gap_warning_ms = 2000
generate_audit = false
editor = ""
```

- `anchor_target_words` is an approximate review/alignment window size. Writers should
  prefer a nearby canonical segment, pause, or speaker boundary when practical.
- `long_gap_warning_ms` controls the warning for inserted text positioned between
  canonical source words separated by a large pause. It does not move canonical timing.
- `generate_audit` controls optional detailed audit persistence; compact provenance and
  statistics remain mandatory.
- an empty `editor` uses the `VISUAL` environment variable and then the `EDITOR`
  environment variable for `revise edit`. Their values must be installed commands such
  as `nano` or `code --wait`; the words `VISUAL` and `EDITOR` are not commands.

Revision batch failure behavior reuses the existing runtime batch policy rather than
introducing a duplicate correction-only setting.

## 8. Future automated-correction configuration

LLM correction is not part of v0.2.0. When implemented, chunk target size, maximum size,
and read-only overlap MUST be configurable in TOML and overrideable by CLI/application
request. Exact default values are deferred until automated-correction benchmarks. No
backend model's maximum context window may be hard-coded into the revision engine.
