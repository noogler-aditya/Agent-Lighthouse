# Architecture

## System Components

- `frontend/` (React + Vite): visual dashboard for traces, spans, tokens, and state
- `backend/` (FastAPI): authenticated API + WebSocket layer over Redis storage
- `sdk/` (Python): instrumentation client for traces, spans, and state updates
- `redis`: persistence and real-time event backbone
- `postgres`: persistent relational storage for user accounts and API keys

## Request and Data Flow

1. Agent code uses SDK to create traces/spans/state updates.
2. SDK sends scoped machine requests to backend (`X-API-Key` with ingestion scopes).
3. UI/session traffic uses Supabase JWT bearer auth (`Authorization: Bearer <token>`).
3. Backend validates input, persists entities in Redis, and broadcasts updates.
4. Frontend pulls trace lists and subscribes to live updates via WebSocket.
5. User inspects graph, token metrics, and agent state from dashboard.

## Trust Boundaries

- SDK and frontend are untrusted clients from backend perspective.
- Backend is the auth boundary and must enforce API key checks.
- Redis should be private to trusted network scope.

## Reliability Considerations

- Backend health depends on Redis availability.
- Frontend should differentiate empty-data state from fetch/auth failures.
- SDK instrumentation must use a consistent active tracer context for decorators.

## Primary Operational Risks

- Misconfigured API keys between frontend/backend/SDK
- CORS misconfiguration causing browser-side request failures
- Redis connectivity failures
- CI failures bypassed without required status checks on `main`
