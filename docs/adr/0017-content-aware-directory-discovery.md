# ADR-0017: Content-aware directory discovery after MVP

## Status

Accepted for the MVP release boundary.

## Context

FR-A05 broadly requires support for audio decodable by FFmpeg. A directly supplied file
already reaches ffprobe regardless of its extension, and the release input matrix covers
WAV, MP3, FLAC, M4A/AAC, Ogg, and Opus. Directory discovery, however, deliberately uses
the configured `input.supported_audio` extensions before inspection.

Simply admitting every regular directory entry would not satisfy the intended contract:
podcast directories commonly contain text, images, checksums, and project files. Those
siblings would become failed transcription jobs rather than structured non-media skips.
Probing all entries during discovery also needs probe-result reuse to avoid doubling I/O
and startup cost during inspection.

## Decision

For MVP, directory batches support the configured and validated standard audio suffixes.
Arbitrary-extension, FFmpeg-decodable files remain supported when supplied directly.

Content-aware arbitrary-format directory discovery is deferred to V2. Its implementation
must:

1. use ffprobe to distinguish audio from ordinary non-media siblings;
2. preserve symlink, recursion, ordering, and warning behavior;
3. report non-audio siblings as structured skips, not failed jobs; and
4. reuse successful probe results during inspection.

This is a narrow deferral of FR-A05, not permission to identify accepted media by suffix
alone: every accepted source is still validated through ffprobe before processing.

## Consequences

- The MVP contract is explicit about its directory-format boundary.
- Common podcast directories remain safe and predictable.
- V2 has a generic design target rather than a transcript- or codec-specific exception.
