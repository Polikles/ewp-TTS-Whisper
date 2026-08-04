# Risk Register

| ID | Risk | Probability | Impact | Mitigation |
|---|---|---:|---:|---|
| R-001 | Incompatible PyTorch/CUDA/WhisperX versions | medium | high | lockfile, doctor, clean-install validation |
| R-002 | Alignment failures for numbers and symbols | high | medium | timestamp provenance, fallback, terminology tests |
| R-003 | Incorrect overlap diarization | high | medium | warnings, preserve overlap, prefer separate channels |
| R-004 | Incorrect stereo classification | medium | high | conservative fallback, manual override, Audacity fixtures |
| R-005 | Output filename collision | medium | high | SHA-256, episode signature, versioning, locks |
| R-006 | OOM or VRAM leak during batch processing | low/medium | high | staged model release, peak metrics, accepted 151-minute RTX 3090 endurance baseline |
| R-007 | Poor recognition of Polish proper names | high | medium | ground truth, v2 dictionary, model comparison |
| R-008 | Slow I/O through `/mnt/d` | medium | low/medium | workdir/cache in WSL ext4, sequential source reads |
| R-009 | Unintended network access | low | high | offline mode, local model paths, network-block tests |
| R-010 | Data loss after failure | low | high | partial/failed state, atomic finalization, fsync/copy-verify |
| R-011 | Unreadable subtitles during fast speech | medium | medium | CPS/line limits, human review corpus, configurable preset |
| R-012 | Ambiguous speaker suffix in filename | medium | low | suffix only in groups or count=1, dry-run preview |
| R-013 | English ASR is supported by multilingual large-v2, but English alignment and end-to-end quality are unvalidated | medium | medium | keep `en`/`auto` available, use a language-appropriate pinned local aligner, and mark English quality as provisional until an English smoke sample and larger corpus pass |
| R-014 | Small untimestamped quality corpus | high | medium | expand with manually corrected archive excerpts; add timestamp/speaker annotations later |
