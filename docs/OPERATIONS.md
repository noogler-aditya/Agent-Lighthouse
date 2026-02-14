# Operations Runbook

## Environment Variables

Backend:

- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_JWT_ISSUER`: Supabase JWT issuer URL (usually `<SUPABASE_URL>/auth/v1`)
- `SUPABASE_JWT_AUDIENCE`: Supabase JWT audience (default `authenticated`)
- `SUPABASE_ROLE_CLAIM`: claim path used for app role mapping (default `app_metadata.role`)
- `SUPABASE_ROLE_MAP`: mapping from Supabase claims to app roles (example: `authenticated:viewer,service_role:admin`)
- `MACHINE_API_KEYS`: scoped machine keys for SDK ingestion
- `ALLOWED_ORIGINS`: comma-separated CORS allowlist
- `REDIS_URL`: Redis connection URL (example: `redis://localhost:6379`)

Frontend:

- `VITE_API_URL`: backend base URL (default: `http://localhost:8000`)
- `VITE_SUPABASE_URL`: Supabase URL used by frontend sign-in
- `VITE_SUPABASE_ANON_KEY`: Supabase anon key for frontend auth

SDK:

- `LIGHTHOUSE_BASE_URL`: backend URL for SDK scripts
- `LIGHTHOUSE_API_KEY`: machine key (must include required scopes)

## Health Checks

Run in this order:

```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
TOKEN=<supabase_access_token>
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/traces
LIGHTHOUSE_API_KEY=local-dev-key LIGHTHOUSE_BASE_URL=http://localhost:8000 python3 sdk/examples/smoke_trace_check.py
```

## Incident Triage

1. Check backend logs for startup/import/auth errors.
2. Verify Redis reachability and health.
3. Validate Supabase JWT verification flow (`Authorization: Bearer <supabase_access_token>`) and machine key scopes.
4. Validate CORS (`ALLOWED_ORIGINS`) includes dashboard origin.
5. Use smoke script to confirm end-to-end ingestion.

## CI/CD Operations

- CI workflow: `.github/workflows/ci.yml`
- CD workflow: `.github/workflows/cd.yml`
- Code scanning workflow: `.github/workflows/codeql.yml`
- Required checks should be enforced via branch protection on `main`.
- If CI fails on PR, workflow comments and applies a `ci-failed` label for follow-up.

## Recovery Playbook

- Backend unavailable: restart backend and validate `/health`.
- Frontend empty with auth errors: verify Supabase env values and token refresh path.
- No traces after healthy API: run smoke script, then refresh dashboard.
- Release regression: revert bad merge or ship patch release and update changelog.
