# ADR-0006: Interface-Independent Application Core

- Status: accepted
- Date: 2026-07-29

## Decision

Pipeline, domain-model, export, and storage logic must not live in CLI handlers. The CLI is an application adapter.

## Rationale

The planned GUI must reuse the same operations and validation without duplicated logic.

## Consequences

Every CLI operation maps to an explicit application service with typed input and output.
