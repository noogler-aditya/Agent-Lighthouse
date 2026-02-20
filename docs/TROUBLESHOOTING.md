# Troubleshooting

## Quick Diagnostic

Run the CLI status check first — it covers most issues:

```bash
pip install agent-lighthouse
agent-lighthouse status
```

This tells you if the backend is reachable and if your API key is valid.

---

## Dashboard Shows No Traces

**Most common cause:** SDK decorators were silently dropping traces. **Fix:** Update to SDK v0.3.1+ (`pip install --upgrade agent-lighthouse`). Decorators now auto-create traces when no active context exists.

**Full checklist:**

1. **Verify API key is set:**
   ```bash
   agent-lighthouse status
   ```
   If auth shows "failed", run `agent-lighthouse init` to set up your key.

2. **Verify backend is reachable:**
   ```bash
   curl https://agent-lighthouse.onrender.com/health
   ```
   Should return `{"status": "healthy", ...}`.

3. **Verify traces are being sent:**
   ```bash
   agent-lighthouse traces --last 5
   ```
   If this returns traces but the dashboard is empty, it's a frontend auth issue.

4. **For local development:**
   - `VITE_API_URL` must point to `http://localhost:8000` (not the Render URL)
   - `ALLOWED_ORIGINS` in backend must include `http://localhost:5173`
   - `JWT_SECRET` and `DATABASE_URL` must be set

---

## 403 Forbidden on SDK Calls

- Ensure your API key starts with `lh_` and matches a key in the dashboard.
- Machine API keys (set via `MACHINE_API_KEYS` env) need explicit scopes: `trace:write|trace:read`.
- Run `agent-lighthouse status` to verify auth.

---

## Tokens Show as 0

- **Local models (Ollama, llama.cpp):** These don't report token usage in the standard format. Pass the LangChain callback handler to extract token counts from model responses:
  ```python
  from agent_lighthouse.adapters.langchain import LighthouseLangChainCallbackHandler
  handler = LighthouseLangChainCallbackHandler()
  chain.invoke({"goal": "..."}, config={"callbacks": [handler]})
  ```
- **OpenAI/Anthropic:** Use `import agent_lighthouse.auto` at the top of your script for automatic token capture.

---

## Auto-Instrumentation Not Working

- `import agent_lighthouse.auto` must be the **very first import** in your application, before any OpenAI/Anthropic/httpx imports.
- Verify it's enabled: `LIGHTHOUSE_AUTO_INSTRUMENT=1` (default).

---

## `pydantic_settings` Error at Backend Startup

**Symptom:** `error parsing value for field "allowed_origins"`

**Fix:** Set `ALLOWED_ORIGINS` as a simple comma-separated string:
```bash
ALLOWED_ORIGINS=http://localhost:5173,https://agent-lighthouse.vercel.app
```

---

## Smoke Script Fails

```bash
LIGHTHOUSE_API_KEY=local-dev-key LIGHTHOUSE_BASE_URL=http://localhost:8000 \
  python3 sdk/examples/smoke_trace_check.py
```

If it fails:
- Confirm backend is running on the same URL.
- Confirm `LIGHTHOUSE_API_KEY` matches a key in `MACHINE_API_KEYS`.
- Check backend logs for auth or Redis errors.

---

## CI Fails on Pull Request

- Open the failed job logs in GitHub Actions.
- Fix the specific failing stage (frontend, backend, SDK, or integration).
- Push new commits — CI re-runs automatically.
