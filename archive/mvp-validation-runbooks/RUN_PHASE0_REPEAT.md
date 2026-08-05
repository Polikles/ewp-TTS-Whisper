# Repeat the Phase 0 integrated job

Run this after [`RUN_PHASE0_INTEGRATED.md`](RUN_PHASE0_INTEGRATED.md) completes. The goal is to prove that a second full job succeeds with the same immutable local resources after the first job's sequential model unloading.

This is a second-process stability check. Longer multi-file same-process testing remains part of the later application E2E suite.

## 1. Restore and verify the environment

In a fresh WSL shell, repeat sections 1–3 of [`RUN_PHASE0_INTEGRATED.md`](RUN_PHASE0_INTEGRATED.md). All eleven input checks must pass. Record the new idle GPU state.

Do not set `HF_TOKEN`. Keep `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`.

## 2. Select distinct second-run artifacts

After restoring the variables, override only the three output paths:

```bash
export EWP_P003_INTEGRATED_JSON="$EWP_PHASE0_SPIKE/evidence/p0-03-integrated-speakers-run2.json"
export EWP_P003_INTEGRATED_TEXT="$EWP_PHASE0_SPIKE/evidence/p0-03-integrated-speakers-run2.txt"
export EWP_P003_INTEGRATED_REPORT="$EWP_PHASE0_SPIKE/evidence/p0-03-integrated-run2-report.json"
```

This preserves the accepted first-run artifacts.

## 3. Repeat the complete job

Run section 4 of [`RUN_PHASE0_INTEGRATED.md`](RUN_PHASE0_INTEGRATED.md) unchanged. Stop on any download, token request, CUDA failure, missing exclusive diarization, or other stage exception.

Expected accepted warnings:

- Pyannote disables TF32 for reproducibility;
- Lightning may upgrade the bundled VAD checkpoint representation in memory;
- Pyannote's statistics-pooling block may emit the already observed degrees-of-freedom warning.

Do not modify installed or cached checkpoints.

## 4. Verify and compare

```bash
test -s "$EWP_P003_INTEGRATED_JSON" && echo "run-2 JSON: present"
test -s "$EWP_P003_INTEGRATED_TEXT" && echo "run-2 text: present"
test -s "$EWP_P003_INTEGRATED_REPORT" && echo "run-2 report: present"
sha256sum "$EWP_P003_INTEGRATED_JSON" "$EWP_P003_INTEGRATED_TEXT"
cat "$EWP_P003_INTEGRATED_REPORT"
```

Compare the second-run hashes with the accepted first run:

```text
JSON=03776be4ca8d26afb9813c2713448557adc108295c27043e5ea232897d6203f7
text=c4ca51d75c7416db6a75d1e8d61b2433c1fcbcf0162c6bf48014342ced98e6c1
```

Matching hashes are preferred and demonstrate byte-for-byte determinism. Different hashes do not automatically fail the backend: retain both files, do not print their transcript content, and report the hashes so the structured outputs can be compared before deciding.

The report must again show:

- 49 segments and 956 words unless a documented nondeterministic difference is found;
- zero untimed or unassigned words and segments;
- both speaker labels;
- post-unload PyTorch allocation near 8.1 MiB after every stage.

Timing may vary with concurrent GPU and desktop activity and need not match exactly.

## Stop point

Send:

```text
idle GPU state:
complete run-2 sanitized report JSON:
run-2 JSON and text SHA-256 values:
hashes match run 1: YES / NO
warnings or errors:
```

Do not send transcript text, audio, tokens, model files, cache paths, or environment dumps.
