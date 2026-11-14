# ADR 0003 — Human approval is a database state, not a UI step

**Status:** accepted · **Date:** November 2026

## Context

Early-warning systems fail dangerously in both directions: a missed warning, or an automated
message that nobody authorised. The brief requires that alerts need authority approval. A UI-only
confirmation would be bypassable by any API client.

## Decision

- Alerts are created as `CANDIDATE` by the policy engine. There is no code path that creates an
  `APPROVED` alert automatically.
- `POST /alerts/{id}/approve` requires `alerts:approve`, a reason of at least 8 characters and a
  language list; it writes `alert_approvals` and an `audit_logs` entry with actor and timestamp.
- Rejection, cancellation and all-clear require reasons and are audited.
- Scenarios write assessments with `is_scenario = true` and cannot produce alerts; operational
  queries filter them out.
- Public endpoints expose only `APPROVED`, `DELIVERED` and `ALL_CLEAR`.

## Consequences

- A district can run the pipeline unattended without any message escaping.
- Approval latency becomes measurable (analytics records mean approval time).
- The workflow needs a second authorised person available; that is a deliberate operational cost.
