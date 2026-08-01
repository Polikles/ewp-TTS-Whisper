# Phase 0 results

Last updated: **2026-08-01**.

This file records accepted, sanitized evidence from the target RTX 3090 WSL workstation. Full lockfiles, generated transcripts, audio, model caches, and tokens remain outside this repository until explicitly promoted or excluded.

## Gate A — base workstation

Status: **PASS**.

See [`VERIFIED_BASELINE.md`](VERIFIED_BASELINE.md).

## Gate B — media preparation

Status: **PASS**.

See [`PHASE0_MEDIA_INVENTORY.md`](PHASE0_MEDIA_INVENTORY.md).

## Gate C — dependency resolution and installation

Status: **PASS**.

```text
Python=3.12.3
uv=0.12.0
resolved_packages=117
installed_packages=116
uv_pip_check=PASS
uv_lock_sha256=a309c86ba2a06b86842ee3cb56dffc76a15e635f72a2f46bdf5847e7ab88c14c
```

Installed versions:

```text
whisperx=3.8.6
torch=2.8.0+cu128
torchaudio=2.8.0+cu128
torchvision=0.23.0+cu128
torchcodec=0.7.0
pyannote.audio=4.0.7
faster-whisper=1.2.1
ctranslate2=4.8.1
huggingface-hub=0.36.2
transformers=4.57.6
triton=3.4.0
```

## Gate D — CUDA execution

Status: **PASS**.

```text
torch=2.8.0+cu128
embedded_cuda=12.8
cuda_available=true
device=NVIDIA GeForce RTX 3090
tensor_test=PASS
allocated_bytes=4000768
peak_allocated_bytes=8002048
```

The small allocation values describe only the diagnostic tensor test, not ASR or diarization peak VRAM.

## Gate E — TorchCodec and FFmpeg

Status: **PASS**.

P0-01 decoded through TorchCodec:

```text
shape=(1, 4578025)
sample_rate=48000
duration_seconds=95.376
```

This confirms that TorchCodec 0.7.0 can load the installed Ubuntu FFmpeg shared libraries and decode the mono PCM fixture.

## Remaining gates

- diarization and exclusive-diarization smoke test;
- sequential model unloading and second-run stability;
- network-blocked offline replay;
- preliminary model comparison and accurate-preset decision;
- promotion of the approved dependency definition and lockfile.

## Compatibility note — Hugging Face CLI

The locked `huggingface-hub==0.36.2` provides the `hf` CLI but does not recognize `hf download --dry-run`. This is a CLI-version capability difference, not a dependency or model-access failure. The model-preparation runbook uses `HfApi.model_info(..., files_metadata=True)` for non-downloading size/revision inspection instead.

## Model acquisition in progress

Public model metadata and immutable snapshots have been obtained successfully:

```text
ASR_repo=Systran/faster-whisper-large-v3
ASR_revision=edaa852ec7e145841d8ffdb056a99866b5f0a478
ASR_files=7
ASR_known_size_bytes=3090839273

Polish_alignment_repo=jonatasgrosman/wav2vec2-large-xlsr-53-polish
Polish_alignment_revision=6b1cea36bd8bc5f65ec8081667cd9c0207d51970
Polish_alignment_files=24
Polish_alignment_known_size_bytes=4170679797
```

Both downloaded snapshot directory names matched the revisions returned by the metadata API.

NLTK `punkt_tab` was downloaded and extracted successfully after running the already locked virtualenv interpreter from `/tmp` with `-P`. The downloader emitted a non-fatal `runpy` warning, and the expected `tokenizers/punkt_tab` directory was verified afterward.

## Gate F — explicit model and data acquisition

Status: **PASS**.

Community-1 gated access and download:

```text
repo=pyannote/speaker-diarization-community-1
revision=3533c8cf8e369892e6b79ff1bf80f7b0286a54ee
files=10
known_size_bytes=33695573
snapshot_revision_match=PASS
```

Final acquisition checks:

```text
NLTK_punkt_tab=PASS
HF_TOKEN_removed=PASS
HF_cache_size=6.8G
NLTK_data_size=15M
```

The Hugging Face token was removed from the shell after the gated snapshot was cached. No token value or full cache path is recorded here.

## Gate G — initial Polish ASR and word alignment

Status: **PASS for ASR/alignment compatibility and gross correctness; local-only VAD replay remains required**.

Workstation context:

```text
idle_gpu=NVIDIA GeForce RTX 3090
idle_memory_used_mib=3250
gpu_memory_total_mib=24576
idle_gpu_utilization_percent=1
```

The idle memory includes the Windows desktop, two 4K displays, browsers, and other visible applications. The successful run retained substantial headroom; headless operation was not required.

Sanitized measurements:

```text
case=P0-01
language=pl
compute_type=float16
batch_size=4
asr_load_seconds=10.457
asr_seconds=4.095
alignment_load_seconds=0.849
alignment_seconds=1.175
asr_torch_peak_mib=0.0
alignment_torch_peak_mib=1785.4
after_asr_unload_torch_mib=0.0
after_alignment_unload_torch_mib=8.1
segments=13
words=226
untimed_segments=0
untimed_words=0
aligned_output_sha256=671626f5ae2b9c18b742d6396f9a64832494d5676cb56c0275e45059fe1b48dc
```

The zero ASR PyTorch peak is expected because CTranslate2 owns the ASR GPU allocation; it is not evidence of zero ASR VRAM use.

Manual review against the 227-word reference found one substitution (`pomielone` instead of `pomylone`, reported confidence 0.922), one short meaning-preserving omission, and minor punctuation differences. No gross hallucination or ordering problem was found. All generated words had timestamps, their order was correct, and the result stayed within the source duration. Exact timestamp accuracy was not evaluated because no timestamped reference exists yet. The basic-usability decision is **PASS**; this clean studio case is not treated as representative quality evidence.

During this run, `vad_method="silero"` downloaded the upstream default branch through Torch Hub. Hugging Face offline variables do not control Torch Hub. This does not invalidate the ASR or alignment results, but it invalidates the run's local-only/reproducibility claim. The corrected runbook uses WhisperX's bundled Pyannote VAD model and preserves the first output separately.

### Accepted bundled-VAD replay

Status: **PASS**.

No network download occurred. All local input checks passed, including the bundled WhisperX VAD model. The transcript content and manual assessment were identical to the initial run.

```text
idle_memory_used_mib=3369
idle_gpu_utilization_percent=1
vad_method=pyannote
asr_load_seconds=6.694
asr_seconds=4.832
alignment_load_seconds=0.893
alignment_seconds=0.998
asr_torch_peak_mib=248.7
alignment_torch_peak_mib=1636.7
after_asr_unload_torch_mib=8.1
after_alignment_unload_torch_mib=8.1
segments=13
words=226
untimed_segments=0
untimed_words=0
aligned_output_sha256=87550f65aa7905990ec64b9b303e95a06e16e3a08ede80c6803dd43a3de517e6
manual_gross_correctness=PASS
```

Pyannote disabled TF32 for reproducibility, as designed. Lightning upgraded the bundled VAD checkpoint representation in memory while loading it. The installed checkpoint must remain unchanged; the suggested permanent in-place upgrade is not part of environment preparation.

## Gate H — Community-1 diarization component

Status: **TECHNICAL PASS; manual speaker-accuracy assessment pending**.

```text
case=P0-03
idle_memory_used_mib=4152
idle_gpu_utilization_percent=18
requested_speakers=2
load_seconds=0.920
diarization_seconds=9.340
torch_peak_mib=1628.8
after_unload_torch_mib=8.1
standard_speakers=2
standard_turns=22
standard_overlap_seconds=59.012
standard_SPEAKER_00_seconds=190.384
standard_SPEAKER_01_seconds=280.749
exclusive_available=true
exclusive_speakers=2
exclusive_turns=50
exclusive_overlap_seconds=0.0
exclusive_SPEAKER_00_seconds=177.540
exclusive_SPEAKER_01_seconds=234.581
standard_sha256=772ff26b3f7becbc2e062cfe8c297a2342c5467198564a3898fc32b32ae3bec1
exclusive_sha256=0a218bf069f874c751d5771653265661f9d3e5b48509535c85b9c58cc81cbc07
```

Community-1 loaded from the immutable local snapshot without a token or network download, returned exactly two labels, exposed regular overlap-aware diarization, and exposed exclusive diarization with no overlaps. GPU allocations returned to 8.1 MiB after unloading.

The TF32 warning is expected and accepted. Pyannote also emitted a `std()` degrees-of-freedom warning from its statistics-pooling block. It did not interrupt inference or produce invalid structural output, so it is retained as a compatibility observation for repeat-run monitoring rather than treated as a failure.

The interval JSON files intentionally contain no transcript text. Because the available reference transcript has no timestamps, it cannot validate speaker-boundary accuracy or the reported 59.012 seconds of regular overlap. Those quality questions remain open for the integrated speaker-labelled transcript and, later, a timestamped speaker reference. In particular, the known presence of three audible overlap regions does not by itself prove that 59.012 seconds of detected overlap is accurate.
