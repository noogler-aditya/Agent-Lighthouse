# Contributing to Agent Lighthouse

Thanks for contributing.

## Before You Start

- Read [README.md](README.md).
- Search existing issues and pull requests before opening a new one.
- For security vulnerabilities, do **not** open a public issue. See [SECURITY.md](SECURITY.md).

## Development Setup

### Option 1: Docker

```bash
docker-compose up --build
```

### Option 2: Local

```bash
# Backend
cd backend
pip install -r requirements.txt
export SUPABASE_URL=http://localhost:54321
export SUPABASE_JWT_ISSUER=http://localhost:54321/auth/v1
export SUPABASE_JWT_AUDIENCE=authenticated
export MACHINE_API_KEYS=local-dev-key:trace:write|trace:read
export ALLOWED_ORIGINS=http://localhost:5173
python3 -m uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
export VITE_SUPABASE_URL=http://localhost:54321
export VITE_SUPABASE_ANON_KEY=<your-supabase-anon-key>
npm run dev

# SDK smoke check
cd sdk
pip install -e .
LIGHTHOUSE_API_KEY=local-dev-key python3 examples/smoke_trace_check.py
```

## Branching and Pull Requests

- Create topic branches from `main`.
- Keep pull requests focused and small.
- Reference issues in PR description (`Fixes #123`).
- Update docs when behavior or interfaces change.

## Required Checks

Your PR should pass:

- Frontend lint/build/tests
- Backend quality checks + tests
- SDK matrix quality checks + tests
- Integration smoke test

These checks run in GitHub Actions (`.github/workflows/ci.yml`).

## Code Style

### Python

- Prefer explicit, readable code.
- Keep functions small and single-purpose.
- Avoid mutable default arguments.

### Frontend

- Follow existing component and CSS conventions.
- Keep rendering states explicit (`loading`, `error`, `empty`, `ready`).
- Prefer icon components over emoji for UI actions.

## Commit Messages

Use clear, scoped messages, for example:

- `feat(frontend): add trace error banner and retry`
- `fix(sdk): unify active tracer context for decorators`
- `docs: add security and support guides`

## Documentation Expectations

When relevant, update:

- [README.md](README.md)
- [SECURITY.md](SECURITY.md)
- [CHANGELOG.md](CHANGELOG.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for major design changes
- [docs/OPERATIONS.md](docs/OPERATIONS.md) for operational changes
