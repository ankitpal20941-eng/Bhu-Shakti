# Security

## 1. Assumptions and threat model

The prototype is designed for a state government network: authenticated staff, district-scoped
data, public read-only citizen endpoints. It assumes TLS termination at a reverse proxy and a
trusted operator. Adversaries considered: an unauthenticated internet user, an authenticated user
trying to read or act outside their district, a malicious upload, and credential stuffing.

Out of scope for this build: nation-state actors, supply-chain compromise, physical access, and
multi-tenant isolation between separate government deployments.

## 2. Authentication

- Passwords are stored as PBKDF2-HMAC-SHA256 hashes with a per-password random salt
  (`app/security.py`). Plaintext passwords are never stored or logged.
- A successful login issues a compact, JWT-shaped token signed with HMAC-SHA256 over
  `header.payload`, containing user id, email, role, district scopes, issued-at and expiry
  (default 12 h). The signing key is `BHUSHAKTI_SECRET_KEY`; in development a per-install key is
  generated at `backend/.dev_secret` and must not be committed.
- The token is delivered as an HttpOnly cookie `bs_session` (`SameSite=Lax`, `Secure` in
  production) and returned in the body for Bearer clients such as the field PWA.
- Every request re-loads the user from the database: disabling an account takes effect
  immediately, even with an unexpired token.
- Login is rate limited per IP (default 10/min) and both success and failure are audited.
- There is **no MFA, SSO or password-reset flow** in this build (see LIMITATIONS).

## 3. Authorisation

- A static permission matrix (`domain.ROLE_PERMISSIONS`) maps seven roles to explicit permission
  strings. Routes declare the permission they need; there is no implicit "admin bypass".
- District scoping is applied in the query layer for every list, detail and mutation. A district
  administrator scoped to `AS-KMR` cannot read `ML-EKH` units, reports or alerts even by guessing
  ids; the API returns 404/403 rather than leaking existence.
- Assignment and alert actions also check the target unit's district.
- Self-deactivation is refused; role and scope changes are audited with before/after values.

## 4. Session and CSRF posture

- The cookie is `HttpOnly` and `SameSite=Lax`, so cross-site POSTs do not carry it in modern
  browsers; JSON bodies are required for mutations (a cross-site HTML form cannot set
  `Content-Type: application/json`).
- CORS is restricted to an explicit allowlist (`BHUSHAKTI_CORS_ORIGINS`), with credentials enabled
  only for those origins.
- Residual risk: there is no CSRF token. If the deployment must support older browsers or
  cross-site embedding, add a double-submit token before exposing the cookie flow beyond a
  controlled network. Bearer-token clients are unaffected.

## 5. Transport and headers

- TLS is expected at the reverse proxy; the app sets `Secure` on the cookie when
  `BHUSHAKTI_ENV=production`.
- Middleware attaches a request id to every response and to error envelopes so support can
  correlate a report with server logs without exposing stack traces to clients.
- Unhandled exceptions are converted to a generic 500 envelope; internal details stay in logs.
- A print stylesheet and frame-denial headers prevent embedding of operational screens in
  third-party pages. See `app/main.py` for the exact header set in this build.

## 6. Input and upload safety

- All request bodies are validated by Pydantic models with bounded lengths and enums.
- Report media: declared MIME must be in the allowlist, magic bytes must match, size ≤ 10 MB,
  ≤ 3 files, EICAR test string rejected, SHA-256 recorded, stored outside the web root with
  random names. No image parsing or EXIF processing is performed (no image AI).
- SQL access goes through SQLAlchemy with bound parameters; there is no string-built SQL.
- Public endpoints are rate limited (5 reports/min/IP) and return generic errors.
- `client_uuid` is pattern-validated to prevent injection into logs or filenames.

## 7. Auditing

`audit_logs` is append-only from the application's perspective and records: timestamp, actor
email, actor role, action (`auth.login`, `alert.approved`, `report.verified`, `user.updated`,
`feature_flag.updated`, `model.activate`, `source.ingest`, …), entity, entity id, reason,
before/after payload, request id and IP.

The audit trail is readable with `audit:read` (platform/state/district admins, analysts,
researchers do not have it). Alert approval, rejection and cancellation are always audited;
priority changes require a reason and are audited.

## 8. Secrets and configuration

| Secret | Handling |
| --- | --- |
| `BHUSHAKTI_SECRET_KEY` | Environment variable in production; generated dev secret otherwise. Rotating it invalidates all sessions. |
| Database credentials | `BHUSHAKTI_DATABASE_URL`; never in source |
| SMS/email keys | none configured; no placeholder keys are accepted as working |

`.dev_secret`, `backend/data/*.db`, `backend/storage/*` and `.env` files must be excluded from
version control. `.env.example` documents names only.

## 9. Deployment checklist

1. `BHUSHAKTI_ENV=production` (disables demo mode, seeded accounts and the demo banner).
2. Set a strong `BHUSHAKTI_SECRET_KEY`; keep it out of the image.
3. Serve over HTTPS; the proxy sets HSTS.
4. Set `BHUSHAKTI_CORS_ORIGINS` to the exact console origin.
5. Create users through administration; do not enable seeded accounts.
6. Restrict `backend/storage` to the service account.
7. Ship the audit log to write-once storage if the jurisdiction requires it.
8. Run one worker process (the in-process scheduler must not run in parallel) or move the
   scheduler to a separate process before scaling out.
9. Configure backups for PostgreSQL and the media directory; test restore.
10. Add CSRF tokens and MFA before exposing the console to the public internet.

## 10. Known gaps

- No MFA, SSO, password reset, or account lockout beyond rate limiting.
- Rate limiting is in-process; a multi-node deployment needs Redis.
- No antivirus beyond the EICAR check and magic-byte validation.
- No field-level encryption at rest (relies on disk/database encryption).
- No automated dependency or container scanning in this repository.
- No CSRF token (see §4).
