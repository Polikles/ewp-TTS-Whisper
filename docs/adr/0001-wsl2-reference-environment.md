# ADR-0001: WSL2 as the Reference Environment

- Status: accepted
- Date: 2026-07-29

## Context

The ML stack is strongly aligned with the Linux CUDA ecosystem, while the user works on Windows.

## Decision

MVP Tier 1: WSL2 + Ubuntu 24.04 LTS + NVIDIA CUDA. Native Linux and native Windows are not required targets.

## Consequences

- the repository, work directories, and model caches reside in the WSL filesystem;
- sources may be read from Windows drives;
- a future Docker image should use the same Linux baseline;
- Ubuntu 26.04 requires separate qualification.
