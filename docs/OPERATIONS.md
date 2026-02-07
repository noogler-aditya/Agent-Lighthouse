# Operations Runbook

## Environment Variables

Backend:

- `LIGHTHOUSE_API_KEY`: required API key for authenticated requests
- `ALLOWED_ORIGINS`: comma-separated CORS allowlist
- `REDIS_URL`: Redis connection URL (example: `redis://localhost:6379`)

Frontend:

- `VITE_API_URL`: backend base URL (default: `http://localhost:8000`)
- `VITE_API_KEY`: key sent as `X-API-Key`

SDK:

- `LIGHTHOUSE_BASE_URL`: backend URL for SDK scripts
- `LIGHTHOUSE_API_KEY`: SDK API key

## Health Checks

Run in this order:

```bash
curl -H "X-API-Key: local-dev-key" http://localhost:8000/health
curl -H "X-API-Key: local-dev-key" http://localhost:8000/api/traces
LIGHTHOUSE_API_KEY=local-dev-key LIGHTHOUSE_BASE_URL=http://localhost:8000 python3 sdk/examples/smoke_trace_check.py
```

## Incident Triage

1. Check backend logs for startup/import/auth errors.
2. Verify Redis reachability and health.
3. Validate API key parity between frontend/backend/SDK.
4. Validate CORS (`ALLOWED_ORIGINS`) includes dashboard origin.
5. Use smoke script to confirm end-to-end ingestion.

## CI/CD Operations

- CI workflow: `.github/workflows/ci.yml`
- CD workflow: `.github/workflows/cd.yml`
- Required checks should be enforced via branch protection on `main`.
- If CI fails on PR, workflow currently auto-closes PR and adds a comment.

## Recovery Playbook

- Backend unavailable: restart backend and validate `/health`.
- Frontend empty with auth errors: align `VITE_API_KEY` and `LIGHTHOUSE_API_KEY`.
- No traces after healthy API: run smoke script, then refresh dashboard.
- Release regression: revert bad merge or ship patch release and update changelog.
