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
project: ./transcriber.toml
user: ~/.config/ewp-transcriber/config.toml
```

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

## 4. `accurate` preset

The MVP preset is optimized for an RTX 3090 and prioritizes quality. It should define:

- a large multilingual model selected through project benchmarks;
- CUDA `float16`;
- a batch size validated by an OOM stability test;
- word alignment;
- full diarization when required;
- no quality-reducing quantization;
- no automatic audio repair.

The ASR model and batch size must remain configurable.

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
