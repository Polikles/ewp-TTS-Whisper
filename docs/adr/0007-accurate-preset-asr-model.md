# ADR-0007: Accurate-Preset ASR Model Selection

- Status: accepted
- Date: 2026-08-02
- Decision owner: EWP-transcripts project owner

## Context

The MVP needs a reproducible ASR model for the `accurate` preset. Upstream descriptions are insufficient for choosing between `large-v2` and `large-v3` on edited Polish podcast material. The decision must remain traceable to project-owned measurements on the target RTX 3090 WSL workstation.

Candidate A's dependency, CUDA, ASR/alignment, diarization, repeatability, and network-blocked offline gates have passed. The validated `large-v3` snapshot is:

```text
repo=Systran/faster-whisper-large-v3
revision=edaa852ec7e145841d8ffdb056a99866b5f0a478
```

The compared corpus contains only three cases. It is sufficient for an initial MVP decision, not for a strong claim that either model is generally more accurate across Polish podcast material. The decision must be rerun when the larger manually verified dataset is available.

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
| P0-01 | `7c5cc9bd72bb1383ce7e33996b5573521277af7fe5f63f5687fe6768cc380c33` | `a06bbc24b898ccbfba5845e544194d19cbe65219b4170be875ee9b6689e15dbc` | 227 |
| P0-02 | `32c19ea948404ed0b08d42ce8a03dbcfc4672248ca7b261550a1d4f88f61c46a` | `c34adb93956e0c5cd04f2abb7b4172046ee9c8120ed48b82db91c54eda3b672f` | 614 |
| P0-03 | `a62e2a771f6a09732541d22834d6be8ea25a486cbd4ab1628a5e7bb9d06076ba` | `9841dbe8eb87ca5dc19632dee9e3ab6ced95c0d6cc5f3629e4fd3c3a453b2172` | 1,141 |

### Lexical accuracy

| Case | Model | WER | CER | Substitutions | Deletions | Insertions | Hypothesis words | Hypothesis SHA-256 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| P0-01 | `large-v2` | 0.00881057 | 0.00326158 | 1 | 1 | 0 | 226 | `ba1bd799f8dbcf5e595fb8caea89fd1937f6ab834ca887a3b63b3e1cb5974303` |
| P0-01 | `large-v3` | 0.01321586 | 0.00456621 | 2 | 1 | 0 | 226 | `6616b5fc9a9f7c36835dfbddd29c8748da2812b9522e9ece8724a9a613c33151` |
| P0-02 | `large-v2` | 0.00814332 | 0.00354359 | 3 | 2 | 0 | 612 | `ce160ba9062d28b3a4880c7ca75bfa03d73bae347e8f8a79f2c01461a82e69bc` |
| P0-02 | `large-v3` | 0.01302932 | 0.00425230 | 6 | 2 | 0 | 612 | `2f8af28e9f73f31bc080b4f15d350350d1c2b2043ac78a62d5f15d8c44493c31` |
| P0-03 | `large-v2` | 0.19106047 | 0.17072846 | 20 | 187 | 11 | 965 | `4debf9955467936c3d565d33219dcc5e1d5a4570412ee308931ed4acd054789a` |
| P0-03 | `large-v3` | 0.18667835 | 0.16939672 | 15 | 191 | 7 | 957 | `0e4aeeb5e664597a1a0806872ca13b2112974b15059f8ad620387b9015ef061d` |
| Macro average | `large-v2` | 0.06933812 | 0.05917788 | n/a | n/a | n/a | n/a | n/a |
| Macro average | `large-v3` | 0.07097451 | 0.05940508 | n/a | n/a | n/a | n/a | n/a |

The formal P0-03 `large-v3` row uses the fresh ASR-only hypothesis. Its lexical score matches the earlier integrated result exactly; its JSON hash differs because the integrated file also contains alignment and speaker metadata. The earlier integrated hash remains in the Phase 0 results.

Across all 1,982 reference words, `large-v2` made 225 errors and `large-v3` made 224. Their supplementary micro WER values are 0.11352170 and 0.11301715. Across all 13,275 normalized reference characters, micro CER is 0.09807910 for `large-v2` and 0.09770245 for `large-v3`. The predefined primary aggregate remains the unweighted macro average.

### Performance

| Case | Model | Load seconds | ASR seconds | Timing context |
|---|---|---:|---:|---|
| P0-01 | `large-v2` | 6.632 | 6.235 | model ran first; load includes first-use VAD/checkpoint overhead |
| P0-01 | `large-v3` | 2.752 | 6.209 | model ran second in the same process |
| P0-02 | `large-v2` | shared | 12.762 | same loaded model instance |
| P0-02 | `large-v3` | shared | 13.879 | same loaded model instance |
| P0-03 | `large-v2` | shared | 19.679 | same loaded model instance |
| P0-03 | `large-v3` | shared | 21.126 | same loaded model instance |

Total measured ASR time was 38.676 seconds for `large-v2` and 41.214 seconds for `large-v3`, approximately 6.6% in favor of `large-v2`. Timing is secondary and comes from one ordered run under changing desktop GPU load. Load times are not directly comparable because `large-v2` paid first-use overhead.

### Qualitative observations

| Case | `large-v2` | `large-v3` |
|---|---|---|
| P0-01 | one substitution and one deletion; slightly better punctuation | one extra substitution (`mogą` instead of `mogły`); punctuation slightly worse |
| P0-02 | three substitutions and two deletions, including `z` instead of `ze`; punctuation slightly better | six substitutions and two deletions; punctuation slightly worse |
| P0-03 | materially more small recognition errors, including `potwierdzam`/`potwierdza` and `kopią wklej`/`kopiuj-wklej`; most overlap omitted | near-perfect outside overlap; fewer substitutions and insertions; recovered several more sentences near overlap, though much simultaneous speech was omitted |

Punctuation is not a deciding factor for this ASR choice. It remains a separate output-quality concern. LLM-based punctuation repair is outside the MVP even if considered in a later project stage.

## Interpretation

- `large-v2` wins macro WER by 0.00163639 (0.164 percentage points) and macro CER by 0.00022720 (0.023 percentage points).
- `large-v2` makes one fewer error on P0-01 and three fewer on representative P0-02.
- `large-v3` makes five fewer errors on difficult P0-03, has one fewer total word error, and is qualitatively better on the most challenging material.
- Both models are excellent on clean cases and both lose substantial simultaneous speech from mixed mono.
- The strongest decision trade-off is `large-v3`'s difficult-case behavior versus `large-v2`'s small clean-case and speed advantage.
- With only three cases, the observed differences may not generalize. No result in this ADR should be treated as a permanent model ranking.

## Decision criteria

Accuracy on manually verified Polish references is primary. The decision must consider:

1. per-case and macro WER/CER;
2. deletion and hallucination behavior, especially on P0-03;
3. qualitative handling of Polish wording and terminology;
4. runtime and resource cost as secondary trade-offs;
5. deterministic local and offline operation.

Do not select a model solely because it wins one aggregate number. Material regressions on the representative P0-02 case or materially worse hallucination behavior require explicit justification.

## Decision

Select `Systran/faster-whisper-large-v2` revision `f0fe81560cb8b68660e564f55dd99207059c092e` for the MVP `accurate` preset.

The owner chose `large-v2` because it won the predefined macro WER/CER comparison, made fewer errors on both clean cases, and was faster in the initial benchmark. This decision explicitly accepts that `large-v3` was materially better on the difficult P0-03 overlap case and made one fewer total word error. Given the very small three-case corpus, neither advantage is considered conclusive enough to override the owner's preference for the predefined macro result and clean-material behavior.

This is an initial baseline, not a permanent model ranking. Reopen this ADR and rerun the same automated comparison on the larger manually verified corpus when it becomes available.

## Consequences

- `large-v2` becomes the default ASR model for the MVP `accurate` preset.
- `large-v3` remains a measured alternative and may be selected through configuration.
- The exact `large-v2` revision must be used for reproducible preparation and recorded in results.
- A larger corpus may reverse this decision; changing the default requires reopening this ADR with new per-case and aggregate evidence.
- Punctuation remains secondary to lexical accuracy and is not delegated to an LLM in the MVP.
