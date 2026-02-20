# Agent Lighthouse SDK (Python)

The official Python SDK for instrumenting AI agents with [Agent Lighthouse](https://agent-lighthouse.vercel.app).

[![PyPI](https://img.shields.io/pypi/v/agent-lighthouse)](https://pypi.org/project/agent-lighthouse/)
[![Python](https://img.shields.io/pypi/pyversions/agent-lighthouse)](https://pypi.org/project/agent-lighthouse/)

## Installation

```bash
pip install agent-lighthouse
```

## CLI — Zero-Config Onboarding

The SDK includes a CLI for quick setup and diagnostics:

```bash
# Interactive login — writes API key to .env automatically
agent-lighthouse init

# Check backend health and auth status
agent-lighthouse status

# List recent traces from terminal
agent-lighthouse traces --last 5
```

Short alias: `al init`, `al status`, `al traces --last 3 --json`

## Quick Start

### 1. Set Your API Key

Run `agent-lighthouse init` (recommended), or set manually:

```bash
export LIGHTHOUSE_API_KEY="lh_your_key_here"
```

### 2. Add Decorators

```python
from agent_lighthouse import trace_agent, trace_tool, trace_llm, get_tracer

@trace_tool("Web Search")
def search_web(query):
    return requests.get(f"https://api.search.com?q={query}").json()

@trace_llm("GPT-4", model="gpt-4-turbo", cost_per_1k_prompt=0.01)
def call_llm(prompt):
    return openai.chat.completions.create(...)

@trace_agent("Researcher")
def research_agent(topic):
    data = search_web(topic)
    summary = call_llm(f"Summarize {data}")
    return summary

# Wrap in a trace context
tracer = get_tracer()
with tracer.trace("Research Workflow"):
    research_agent("AI Trends 2025")
```

### 3. Run It

Just run your script. Traces appear on the dashboard automatically.

## Auto-Instrumentation

No decorators required — import once at the top of your script:

```python
import agent_lighthouse.auto
```

This automatically instruments:
- OpenAI and Anthropic client calls
- HTTP requests to known LLM endpoints
- LangChain/LangGraph, CrewAI frameworks (when installed)

Content capture is **off by default**:

```bash
export LIGHTHOUSE_CAPTURE_CONTENT=true
```

## LangChain / LangGraph

Pass the callback handler to capture LLM calls, chains, and tools:

```python
from agent_lighthouse.adapters.langchain import LighthouseLangChainCallbackHandler

handler = LighthouseLangChainCallbackHandler()
chain.invoke({"goal": "..."}, config={"callbacks": [handler]})
```

## State Inspection

Push live state to the dashboard for real-time debugging:

```python
tracer = get_tracer()
tracer.update_state(
    memory={"goal": "...", "plan": plan},
    context={"current_step": "planning"},
    variables={"plan_length": len(plan)},
)
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `LIGHTHOUSE_API_KEY` | Your API key (starts with `lh_`) | *None* |
| `LIGHTHOUSE_BASE_URL` | Backend API URL | `https://agent-lighthouse.onrender.com` |
| `LIGHTHOUSE_AUTO_INSTRUMENT` | Enable auto-instrumentation | `1` |
| `LIGHTHOUSE_CAPTURE_CONTENT` | Capture request/response payloads | `false` |
| `LIGHTHOUSE_LLM_HOSTS` | Extra LLM hosts to instrument | `""` |
| `LIGHTHOUSE_PRICING_JSON` | Pricing override JSON string | `""` |
| `LIGHTHOUSE_PRICING_PATH` | Pricing override JSON file path | `""` |
| `LIGHTHOUSE_DISABLE_FRAMEWORKS` | Disable framework adapters (csv) | `""` |
