# Operations Runbook

## Environment Variables

Backend:

- `JWT_SECRET`: signing key for user bearer tokens
- `AUTH_USERS`: demo/local credential map (`username:password:role`)
- `MACHINE_API_KEYS`: scoped machine keys for SDK ingestion
- `ALLOWED_ORIGINS`: comma-separated CORS allowlist
- `REDIS_URL`: Redis connection URL (example: `redis://localhost:6379`)

Frontend:

- `VITE_API_URL`: backend base URL (default: `http://localhost:8000`)
- `VITE_AUTH_USERNAME` / `VITE_AUTH_PASSWORD`: optional local bootstrap credentials

SDK:

- `LIGHTHOUSE_BASE_URL`: backend URL for SDK scripts
- `LIGHTHOUSE_API_KEY`: machine key (must include required scopes)

## Health Checks

Run in this order:

```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
TOKEN=$(curl -s http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d '{"username":"viewer","password":"viewer"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/traces
LIGHTHOUSE_API_KEY=local-dev-key LIGHTHOUSE_BASE_URL=http://localhost:8000 python3 sdk/examples/smoke_trace_check.py
```

## Incident Triage

1. Check backend logs for startup/import/auth errors.
2. Verify Redis reachability and health.
3. Validate user auth flow (`/api/auth/login`) and machine key scopes.
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
- Frontend empty with auth errors: verify bearer login and token refresh path.
- No traces after healthy API: run smoke script, then refresh dashboard.
- Release regression: revert bad merge or ship patch release and update changelog.
