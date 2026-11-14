# ADR 0007 — Client-generated UUIDs and idempotent batch sync

**Status:** accepted · **Date:** November 2026

## Context

Field officers work without connectivity. Retrying a batch after a dropped connection must not
create duplicate hazard reports, and the UI must never claim a report was delivered when the
server has not acknowledged it.

## Decision

- The device generates a `client_uuid` once, stores the report in IndexedDB and reuses the same id
  for every retry.
- `reports.client_uuid` is unique; `POST /reports` and `POST /reports/sync` return the existing row
  with `duplicate: true` instead of inserting again.
- Sync returns a per-item status (`accepted` / `duplicate` / `failed` + error). The device marks an
  item synced only on `accepted` or `duplicate`, and stores the server id.
- Media is only attached in the online path; the queue is text + GPS.
- Reports are immutable evidence: conflicts are resolved by submitting another report, never by
  merging or overwriting.

## Consequences

- Double taps, offline retries and duplicate batches are safe.
- The server must validate that `client_uuid` looks like an id (pattern check) so it cannot be
  abused as free text.
- There is no background sync registration; the officer presses "Sync now" and sees the queue.
