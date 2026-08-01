# Verified workstation baseline

Verification date: **2026-07-31**.

This record contains non-secret facts reported from the target EWP-transcripts workstation before installing project ML dependencies.

## Host and WSL

| Component | Verified value | Status |
|---|---|---|
| Windows build | `10.0.26200.8875` | compatible |
| Windows release family | Windows 11, version 25H2 build family | compatible |
| WSL | `2.7.11.0` | compatible |
| WSL kernel | `6.18.33.2-2`; Ubuntu reports `6.18.33.2-microsoft-standard-WSL2` | compatible |
| Distribution | `Ubuntu-24.04`, WSL generation 2 | compatible |
| Ubuntu | `24.04.4 LTS (Noble Numbat)` | reference environment |
| Architecture | `x86_64` | compatible |

PowerShell's `Get-ComputerInfo` reported `Windows 10 Pro`, but build `26200` belongs to the Windows 11 25H2 build family according to Microsoft's Windows 11 release information. This is treated as a stale product-name label. The exact displayed edition may be confirmed with `winver`, but it does not block the spike.

Source: [Microsoft — Windows 11 release information](https://learn.microsoft.com/windows/release-health/windows11-release-information).

## GPU

| Component | Verified value | Status |
|---|---|---|
| GPU | NVIDIA GeForce RTX 3090 | reference hardware |
| VRAM | 24,576 MiB reported | compatible |
| Windows NVIDIA driver | `610.62` | detected |
| WSL NVIDIA interface | `610.43.02`, KMD `610.62` | detected |
| Reported CUDA UMD compatibility | `13.3` | detected; not a PyTorch runtime selection |
| `nvidia-smi` inside WSL | works on normal `PATH` | pass |

GPU passthrough is operational. CUDA-enabled PyTorch remains to be validated inside the isolated spike environment.

## Base tools

| Tool | Verified value | Status |
|---|---|---|
| System Python | `3.12.3` | compatible |
| uv | `0.12.0` | compatible; record in spike report |
| Git | `2.43.0` | compatible |
| FFmpeg | `6.1.1-3ubuntu5` | compatible |
| ffprobe | `6.1.1-3ubuntu5` | compatible |
| Linux-home filesystem | 1007 GB total, 954 GB available | sufficient for spike |
| PyTorch | not installed | expected clean starting point |

## Baseline conclusion

The workstation is ready for the Phase 0 dependency and GPU compatibility spike. No base-system installation is required before creating the isolated spike environment.

The repository is cloned at `/home/linuch/transkrypcje/ewp-transcripts`. The spike workspace and external test data must also remain under `/home/linuch`, not under `/mnt/c/Users/DS`.
