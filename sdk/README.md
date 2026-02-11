# Agent Lighthouse SDK (Python)

The official Python client for instrumenting AI agents with Agent Lighthouse.

## Features

- **Automatic Tracing**: Decorators for agents, tools, and LLM calls.
- **Async Support**: Fully compatible with async/await workflows.
- **State Management**: Expose internal agent state (memory, context) for real-time inspection.
- **Token Tracking**: Automatically capture token usage and costs from LLM responses.

## Installation

Install from PyPI:

```bash
pip install agent-lighthouse
```

Or install from source in development mode:

```bash
cd sdk
pip install -e .
```

## Quick Start

### 1. Initialize Tracer

```python
from agent_lighthouse import LighthouseTracer

# Use your API Key (starts with lh_)
tracer = LighthouseTracer(api_key="lh_...")
```

### 2. Add Decorators

Wrap your functions with `@trace_agent`, `@trace_tool`, or `@trace_llm`.

```python
from agent_lighthouse import trace_agent, trace_tool, trace_llm

@trace_tool("Web Search")
def search_web(query):
    # ... logic ...
    return results

@trace_llm("GPT-4", model="gpt-4-turbo", cost_per_1k_prompt=0.01)
def call_llm(prompt):
    # ... call OpenAI ...
    return response

@trace_agent("Researcher")
def run_research_agent(topic):
    data = search_web(topic)
    summary = call_llm(f"Summarize {data}")
    return summary
```

### 3. Run It

Just run your script as normal. The SDK will automatically send traces to the backend.

## State Inspection

Allow humans to inspect and modify agent state during execution:

```python
from agent_lighthouse import get_tracer

@trace_agent("Writer")
def writer_agent():
    tracer = get_tracer()
    
    # Expose state
    tracer.update_state(
        memory={"draft": "Initial draft..."},
        context={"tone": "Professional"}
    )
    
    # ... execution continues ...
```

## Configuration

You can configure the SDK via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `LIGHTHOUSE_API_KEY` | Your machine API key | `None` |
| `LIGHTHOUSE_BASE_URL` | URL of the backend API | `http://localhost:8000` |
