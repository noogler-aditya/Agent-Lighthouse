# Troubleshooting

## Dashboard Shows "No traces yet"

Use this sequence to determine whether it is truly empty data or a hidden error.

1. Verify backend health:
   - `curl http://localhost:8000/health/live`
   - `curl http://localhost:8000/health/ready`
2. Verify traces endpoint:
   - `TOKEN=<supabase_access_token>`
   - `curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/traces`
3. Verify frontend env:
   - `VITE_API_URL` points to backend
   - `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are set correctly
4. Verify backend env:
   - `SUPABASE_URL`, `SUPABASE_JWT_ISSUER`, and `SUPABASE_JWT_AUDIENCE` are set
   - `MACHINE_API_KEYS` includes SDK scope if SDK ingestion is used
   - `ALLOWED_ORIGINS` includes `http://localhost:5173`

## `pydantic_settings` Error Parsing `allowed_origins`

Symptom:

- Backend fails at startup with `error parsing value for field "allowed_origins"`.

Cause:

- `ALLOWED_ORIGINS` value is not in expected format.

Fix:

- For local dev, set a comma-separated string:
  - `ALLOWED_ORIGINS=http://localhost:5173`
- In Docker/compose, ensure env value does not include malformed JSON.

## Smoke Script Fails

Run:

```bash
LIGHTHOUSE_API_KEY=local-dev-key LIGHTHOUSE_BASE_URL=http://localhost:8000 python3 sdk/examples/smoke_trace_check.py
```

If it fails:

- confirm backend is running on the same URL
- confirm machine key in `LIGHTHOUSE_API_KEY` is present in `MACHINE_API_KEYS`
- inspect backend logs for auth/Redis errors

## CI Fails on Pull Request

- Open failed job logs in Actions.
- Fix the specific failing stage (frontend, backend, sdk, or integration).
- Push new commits; CI will re-run automatically.
