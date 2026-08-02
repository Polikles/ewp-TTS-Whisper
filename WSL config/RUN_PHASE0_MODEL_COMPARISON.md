# Run the Phase 0 `large-v2` versus `large-v3` comparison

Run this only after [`PREPARE_PHASE0_MODEL_COMPARISON.md`](PREPARE_PHASE0_MODEL_COMPARISON.md) passes and ADR-0007 contains both immutable model revisions and all six corpus hashes.

The benchmark generates fresh ASR-only hypotheses for all three cases with both models, applies identical lexical normalization, and produces one sanitized aggregate report. It does not run alignment or diarization because this decision concerns the ASR model.

## 1. Restore paths and local-only controls

```bash
export EWP_PHASE0_REPO="$HOME/transkrypcje/ewp-transcripts"
export EWP_PHASE0_SPIKE="$HOME/transkrypcje/ewp-transcripts-spike"
export EWP_PHASE0_DATA="$HOME/transkrypcje/ewp-transcripts-testdata/phase0"
export HF_HOME="$HOME/.cache/huggingface"
export PYANNOTE_METRICS_ENABLED=0

export EWP_ASR_V2_REVISION="f0fe81560cb8b68660e564f55dd99207059c092e"
export EWP_ASR_V3_REVISION="edaa852ec7e145841d8ffdb056a99866b5f0a478"
export EWP_ASR_V2_SNAPSHOT="$HF_HOME/hub/models--Systran--faster-whisper-large-v2/snapshots/$EWP_ASR_V2_REVISION"
export EWP_ASR_V3_SNAPSHOT="$HF_HOME/hub/models--Systran--faster-whisper-large-v3/snapshots/$EWP_ASR_V3_REVISION"
export EWP_COMPARISON_OUTPUT="$EWP_PHASE0_SPIKE/evidence/asr-model-comparison"

export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
unset HF_TOKEN
```

The application-repository path contains only the benchmark utility; all transcript-bearing hypotheses remain in the external spike evidence directory.

## 2. Verify inputs and utility

```bash
test -x "$EWP_PHASE0_SPIKE/.venv/bin/python" && echo "locked Python: present"
test -f "$EWP_PHASE0_REPO/tools/phase0_compare_asr_models.py" && echo "comparison utility: present"
test -f "$EWP_PHASE0_REPO/tools/phase0_score_transcript.py" && echo "lexical scorer: present"
test -d "$EWP_ASR_V2_SNAPSHOT" && echo "large-v2 snapshot: present"
test -d "$EWP_ASR_V3_SNAPSHOT" && echo "large-v3 snapshot: present"
test "$PYANNOTE_METRICS_ENABLED" = 0 && echo "pyannote telemetry: disabled"
test "$HF_HUB_OFFLINE" = 1 && echo "Hub offline mode: enabled"
test "$TRANSFORMERS_OFFLINE" = 1 && echo "Transformers offline mode: enabled"
test -z "${HF_TOKEN:-}" && echo "HF_TOKEN: absent"
```

Expected: all nine checks pass.

The utility re-hashes all six corpus inputs and verifies both snapshot basenames before loading WhisperX. Any mismatch stops the run.

## 3. Record idle GPU state

```bash
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu \
    --format=csv,noheader,nounits
```

Keep other GPU load reasonably stable, but normal Windows desktop use is acceptable. Accuracy is primary; timing is secondary.

## 4. Run all six ASR hypotheses and scores

```bash
(
    cd /tmp
    "$EWP_PHASE0_SPIKE/.venv/bin/python" -P \
        "$EWP_PHASE0_REPO/tools/phase0_compare_asr_models.py" \
        --data-root "$EWP_PHASE0_DATA" \
        --output-dir "$EWP_COMPARISON_OUTPUT" \
        --large-v2 "$EWP_ASR_V2_SNAPSHOT" \
        --large-v3 "$EWP_ASR_V3_SNAPSHOT"
)
```

Expected accepted warnings:

- bundled Pyannote VAD may report an in-memory Lightning checkpoint upgrade;
- Pyannote disables TF32 for reproducibility.

Stop on any download, token request, hash mismatch, revision mismatch, CUDA error, or inference exception.

The command prints only the sanitized comparison report, not transcript text.

## 5. Verify outputs

```bash
test -s "$EWP_COMPARISON_OUTPUT/comparison-report.json" \
    && echo "comparison report: present"

for model in large-v2 large-v3; do
    for case_id in p0-01 p0-02 p0-03; do
        test -s "$EWP_COMPARISON_OUTPUT/$case_id-$model.json" \
            || echo "missing hypothesis: $case_id-$model"
    done
done

sha256sum "$EWP_COMPARISON_OUTPUT/comparison-report.json"
cat "$EWP_COMPARISON_OUTPUT/comparison-report.json"
```

Expected:

- six non-empty hypothesis JSON files;
- one report containing both models and all three cases;
- normalization `ewp-phase0-lexical-v1` for every case;
- macro-average WER and CER for both candidates;
- small post-unload PyTorch allocations.

## 6. Manual qualitative review

Do not decide from macro WER alone. Review both model outputs locally against each reference, concentrating on:

- P0-02 representative Polish wording, names, numbers, and omissions;
- hallucinations and repetitions;
- whether either candidate makes materially worse errors despite a similar WER;
- P0-03 deletion and overlap behavior;
- punctuation as a separate qualitative concern.

Do not send full transcript excerpts unless a short example is necessary to explain a decision-relevant difference.

## Stop point

Send:

```text
nine preflight checks: PASS / FAIL
idle GPU state:
complete comparison-report.json:
comparison report SHA-256:
manual P0-01 preference and reason:
manual P0-02 preference and reason:
manual P0-03 preference and reason:
overall candidate preference, if clear:
warnings or errors:
```

Do not modify ADR-0007's status yet. Results and qualitative evidence must be recorded before the decision is accepted.
