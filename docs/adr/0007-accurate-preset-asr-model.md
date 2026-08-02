# ADR-0007: Accurate-Preset ASR Model Selection

- Status: proposed
- Date: 2026-08-02
- Decision owner: EWP-transcripts project owner

## Context

The MVP needs a reproducible ASR model for the `accurate` preset. Upstream descriptions are insufficient for choosing between `large-v2` and `large-v3` on edited Polish podcast material. The decision must remain traceable to project-owned measurements on the target RTX 3090 WSL workstation.

Candidate A's dependency, CUDA, ASR/alignment, diarization, repeatability, and network-blocked offline gates have passed. The validated `large-v3` snapshot is:

```text
repo=Systran/faster-whisper-large-v3
revision=edaa852ec7e145841d8ffdb056a99866b5f0a478
```

The immutable `large-v2` revision will be recorded before its first inference run.

## Decision status

No model has been selected yet. Change this ADR to `accepted` only after every required result field below is populated and the project owner approves the interpretation.

## Comparison method

### Corpus

Use the external, uncommitted Phase 0 corpus:

| Case | Material | Role in decision |
|---|---|---|
| P0-01 | short, clean, single-speaker Polish studio audio | basic accuracy and regression case |
| P0-02 | representative single-speaker Polish recording | primary realistic lexical-quality case |
| P0-03 | two speakers deliberately mixed into mono, with heavy overlap | stress case and deletion/overlap behavior |

All three reference transcripts are manually verified and have no timestamps. Record audio and reference SHA-256 values in the results table; do not commit audio or transcript text to this repository.

### Fixed inference controls

Both candidates must use the same:

- audio files;
- Python and locked dependency environment;
- CUDA device;
- `float16` compute type;
- ASR batch size 4;
- explicit Polish language (`pl`);
- transcription task;
- bundled Pyannote VAD;
- VAD and ASR options;
- local immutable model loading;
- connected/offline state during the comparison run.

Only the ASR model snapshot may differ. Fresh hypotheses must be generated for both candidates through the same comparison script; do not compare a new candidate against an output produced by a materially different pipeline.

### Lexical normalization and metrics

Use [`../../tools/phase0_score_transcript.py`](../../tools/phase0_score_transcript.py) with normalization version:

```text
ewp-phase0-lexical-v1
```

The scorer concatenates `segments[].text` from each hypothesis JSON and ignores timestamps, confidence values, word objects, and speaker metadata. It applies Unicode NFC, case folding, punctuation-to-space conversion, and whitespace collapse. It preserves Polish diacritics, repetitions, filler words, symbols, and digit-versus-written-number forms.

Record per case:

- WER and CER;
- substitutions, deletions, and insertions;
- reference and hypothesis word counts;
- model load and ASR duration;
- hypothesis SHA-256;
- qualitative Polish terminology, hallucination, repetition, and punctuation observations.

Calculate unweighted macro-average WER and CER across P0-01, P0-02, and P0-03 so that the longest recording does not dominate. Also retain each case separately. P0-03 is an intentional mixed-overlap stress case: its deletion-heavy score must remain visible, but it must not be misrepresented as ordinary clean-speech accuracy.

Untimestamped references support WER/CER but not word-timestamp MAE or DER/JER. Those metrics are outside this ADR's evidence.

## Results

### Reproducibility metadata

| Item | `large-v2` | `large-v3` |
|---|---|---|
| Repository | `Systran/faster-whisper-large-v2` | `Systran/faster-whisper-large-v3` |
| Immutable revision | `f0fe81560cb8b68660e564f55dd99207059c092e` | `edaa852ec7e145841d8ffdb056a99866b5f0a478` |
| Model metadata files/bytes | 6 / 3,089,582,354 | 7 / 3,090,839,273 |
| Dependency lock SHA-256 | `a309c86ba2a06b86842ee3cb56dffc76a15e635f72a2f46bdf5847e7ab88c14c` | same |
| Normalization | `ewp-phase0-lexical-v1` | same |

### Corpus provenance

| Case | Audio SHA-256 | Reference SHA-256 | Reference words after normalization |
|---|---|---|---:|
| P0-01 | `7c5cc9bd72bb1383ce7e33996b5573521277af7fe5f63f5687fe6768cc380c33` | `a06bbc24b898ccbfba5845e544194d19cbe65219b4170be875ee9b6689e15dbc` | pending |
| P0-02 | `32c19ea948404ed0b08d42ce8a03dbcfc4672248ca7b261550a1d4f88f61c46a` | `c34adb93956e0c5cd04f2abb7b4172046ee9c8120ed48b82db91c54eda3b672f` | pending |
| P0-03 | `a62e2a771f6a09732541d22834d6be8ea25a486cbd4ab1628a5e7bb9d06076ba` | `9841dbe8eb87ca5dc19632dee9e3ab6ced95c0d6cc5f3629e4fd3c3a453b2172` | 1,141 |

### Lexical accuracy

| Case | Model | WER | CER | Substitutions | Deletions | Insertions | Hypothesis words | Hypothesis SHA-256 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| P0-01 | `large-v2` | pending | pending | pending | pending | pending | pending | pending |
| P0-01 | `large-v3` | pending | pending | pending | pending | pending | pending | pending |
| P0-02 | `large-v2` | pending | pending | pending | pending | pending | pending | pending |
| P0-02 | `large-v3` | pending | pending | pending | pending | pending | pending | pending |
| P0-03 | `large-v2` | pending | pending | pending | pending | pending | pending | pending |
| P0-03 | `large-v3` | 0.18667835 | 0.16939672 | 15 | 191 | 7 | 957 | `03776be4ca8d26afb9813c2713448557adc108295c27043e5ea232897d6203f7` |
| Macro average | `large-v2` | pending | pending | n/a | n/a | n/a | n/a | n/a |
| Macro average | `large-v3` | pending | pending | n/a | n/a | n/a | n/a | n/a |

The current P0-03 `large-v3` row comes from the accepted integrated output. The formal comparison may replace it with a fresh ASR-only hypothesis if the fixed comparison pipeline produces different segmentation or text. Any replacement must retain both hashes and explain the difference.

### Performance

| Case | Model | Load seconds | ASR seconds | Timing context |
|---|---|---:|---:|---|
| P0-01 | `large-v2` | pending | pending | pending |
| P0-01 | `large-v3` | pending | pending | pending |
| P0-02 | `large-v2` | pending | pending | pending |
| P0-02 | `large-v3` | pending | pending | pending |
| P0-03 | `large-v2` | pending | pending | pending |
| P0-03 | `large-v3` | pending | pending | pending |

### Qualitative observations

| Case | `large-v2` | `large-v3` |
|---|---|---|
| P0-01 | pending | one substitution, one short omission, minor punctuation differences in the earlier integrated check |
| P0-02 | pending | pending |
| P0-03 | pending | non-overlapping speech strong; heavy mixed overlap causes deletion-dominated failure |

## Decision criteria

Accuracy on manually verified Polish references is primary. The decision must consider:

1. per-case and macro WER/CER;
2. deletion and hallucination behavior, especially on P0-03;
3. qualitative handling of Polish wording and terminology;
4. runtime and resource cost as secondary trade-offs;
5. deterministic local and offline operation.

Do not select a model solely because it wins one aggregate number. Material regressions on the representative P0-02 case or materially worse hallucination behavior require explicit justification.

## Decision

Pending comparison.

## Consequences

Pending decision. Once accepted, update:

- [`../14-dependency-baseline.md`](../14-dependency-baseline.md);
- accurate-preset configuration documentation;
- model preparation and installation runbooks;
- Phase 0 results and work status;
- the promoted dependency definition and lockfile metadata.
