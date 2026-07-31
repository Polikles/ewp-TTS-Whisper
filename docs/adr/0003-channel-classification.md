# ADR-0003: Conservative Channel Classification

- Status: accepted
- Date: 2026-07-29

## Decision

- confident dual mono → use one channel;
- confident split speakers → process channels separately;
- ambiguous stereo → warn and use one channel;
- the user may override the mode.

## Rationale

Aggressively transcribing both channels and deduplicating text could remove legitimate repetitions and increase processing cost.

## Consequences

Advanced cross-channel deduplication is deferred to version 2.
