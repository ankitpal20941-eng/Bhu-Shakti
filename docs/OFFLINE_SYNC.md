# Offline synchronisation

## 1. Goals

A field officer in a landslide-prone area often has no connectivity. The requirement is: capture a
report once, do not lose it, and never show it as delivered until the server has acknowledged it.

Two mechanisms cover different needs:

| Mechanism | Scope |
| --- | --- |
| Service worker (`frontend/public/sw.js`) | App shell + a few read-only GETs, network-first with cache fallback |
| IndexedDB queue (`frontend/src/lib/offline.ts`) | Field reports captured without connectivity |

Writes are never cached or replayed by the service worker. The queue owns retries.

## 2. Queue schema

IndexedDB database `bhushakti-field`, object store `report-queue`, key path `client_uuid`:

```ts
{
  client_uuid: string;      // generated once, never regenerated
  created_at: string;       // ISO timestamp
  synced: boolean;
  server_id: number | null; // set only from a server response
  error: string | null;
  payload: {                // sent as-is to /reports/sync
    client_uuid, hazard_type, description, lat?, lon?,
    gps_accuracy_m?, observed_at, consent, anonymous,
    device_id, reporter_name?
  }
}
```

`localStorage["bhushakti-field-meta"]` holds `device_id` (stable per browser) and `last_synced`.

## 3. Capture flow

```
user submits
   │
   ├─ online ──► POST /api/v1/reports (multipart)
   │                 ├─ 2xx ──► success toast; queue untouched
   │                 └─ error ──► enqueue payload, show error + "kept in queue"
   │
   └─ offline ─► enqueue payload, show "queued on this device, not synced"
```

Consent is mandatory before either path; the API enforces it again (422). Photos are attached
only in the online path — the offline queue does not persist media (see LIMITATIONS).

## 4. Sync flow

`POST /api/v1/reports/sync` with `{items: [payload, ...]}` returns one result per item:

```json
{
  "accepted": 1, "duplicates": 1, "failed": 0,
  "results": [
    {"client_uuid": "…", "status": "accepted", "id": 42},
    {"client_uuid": "…", "status": "duplicate", "id": 41},
    {"client_uuid": "…", "status": "failed", "error": "Consent is required …"}
  ]
}
```

Client rules:

- `accepted` or `duplicate` → set `synced = true`, store `server_id` (duplicates return the
  original id), write `last_synced`.
- `failed` → keep `synced = false`, store the server's error string, leave it in the queue for a
  human to fix; it is not silently dropped.
- Network failure → nothing is marked; the queue is unchanged.

Only after the server responds is a report shown as `SYNCED · id N`. The UI never labels a queued
item "sent".

## 5. Idempotency and conflicts

- `reports.client_uuid` is `UNIQUE`. A replay returns the existing row with `duplicate: true`
  before any new row is created, so double taps and retried batches cannot duplicate reports.
- `client_uuid` must match `[A-Za-z0-9._:-]{8,64}`.
- Duplicate suppression happens server-side, not by comparing descriptions.
- Conflicting edits are not merged: reports are append-only evidence. A second observation is a
  second report; verification is one-way.
- Server time is authoritative for `created_at`; the device's `observed_at` is kept and shown.

## 6. Read-only caching

The service worker caches the shell (`/`, `/index.html`, manifest, icon) and, network-first,
`/risk/summary`, `/risk-zones`, `/public/*`, `/health`. If the network fails and a cached copy
exists it is served; otherwise a JSON 503 with code `offline` is returned. Operational writes are
never intercepted.

## 7. Failure modes

| Situation | Behaviour |
| --- | --- |
| Device storage full / IndexedDB blocked | Enqueue throws; the UI shows the error and keeps the form filled |
| Token expired during sync | API returns 401; the queue is retained, user signs in, sync again |
| Server rejects an item | Item stays with the error text; user corrects and resubmits as a new report |
| Duplicate batch after reconnection | Server marks all as `duplicate`; client resolves ids and marks synced |
| Clock skew | Server timestamps win; `observed_at` is preserved separately |

## 8. What is not implemented

- No background sync API (`SyncManager`) registration; the user presses "Sync now".
- No media queue, no compression, no resumable uploads.
- No conflict UI (last-write-wins does not apply because reports are immutable).
- No automated test of the browser queue; the server contract is tested.
