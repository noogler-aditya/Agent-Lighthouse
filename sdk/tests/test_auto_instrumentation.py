import types
import sys
import pytest


class FakeTracer:
    def __init__(self):
        self.trace_id = None
        self.span_id = None
        self.trace_calls = 0
        self.span_calls = 0
        self.tokens = []
        self.outputs = []
        self.capture_output_enabled = True

    def trace(self, name, description=None, metadata=None):
        class _Ctx:
            def __init__(self, outer):
                self.outer = outer
                self.prev = outer.trace_id
            def __enter__(self):
                self.outer.trace_id = f"trace-{self.outer.trace_calls}"
                self.outer.trace_calls += 1
                return {"trace_id": self.outer.trace_id}
            def __exit__(self, exc_type, exc, tb):
                self.outer.trace_id = self.prev
        return _Ctx(self)

    def span(self, name, kind="internal", agent_id=None, agent_name=None, input_data=None, attributes=None):
        class _Ctx:
            def __init__(self, outer):
                self.outer = outer
                self.prev = outer.span_id
            def __enter__(self):
                self.outer.span_id = f"span-{self.outer.span_calls}"
                self.outer.span_calls += 1
                return {"span_id": self.outer.span_id}
            def __exit__(self, exc_type, exc, tb):
                self.outer.span_id = self.prev
        return _Ctx(self)

    def record_tokens(self, prompt_tokens=0, completion_tokens=0, cost_usd=0.0, model=None):
        self.tokens.append((prompt_tokens, completion_tokens, cost_usd, model))

    def record_output(self, output_data):
        self.outputs.append(output_data)


class FakeUsage:
    def __init__(self, prompt, completion):
        self.prompt_tokens = prompt
        self.completion_tokens = completion


class FakeAnthropicUsage:
    def __init__(self, prompt, completion):
        self.input_tokens = prompt
        self.output_tokens = completion


class FakeResponse:
    def __init__(self, usage):
        self.usage = usage


class FakeRequestsResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = "ok"

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def reset_auto(monkeypatch):
    import agent_lighthouse.auto as auto
    auto.uninstrument()
    auto._ORIGINALS.clear()
    auto._INSTRUMENTED = False
    monkeypatch.delenv("LIGHTHOUSE_CAPTURE_CONTENT", raising=False)
    monkeypatch.delenv("LIGHTHOUSE_AUTO_INSTRUMENT", raising=False)
    monkeypatch.delenv("LIGHTHOUSE_LLM_HOSTS", raising=False)
    monkeypatch.delenv("LIGHTHOUSE_PRICING_JSON", raising=False)
    monkeypatch.delenv("LIGHTHOUSE_PRICING_PATH", raising=False)
    yield
    auto.uninstrument()


def _install_fake_openai():
    module = types.ModuleType("openai")

    class ChatCompletion:
        @staticmethod
        def create(*args, **kwargs):
            return FakeResponse(FakeUsage(10, 5))

    class _Completions:
        @staticmethod
        def create(*args, **kwargs):
            return FakeResponse(FakeUsage(7, 3))

    class _Chat:
        completions = _Completions()

    module.ChatCompletion = ChatCompletion
    module.chat = _Chat()

    sys.modules["openai"] = module
    return module


def _install_fake_anthropic():
    module = types.ModuleType("anthropic")

    class _Messages:
        @staticmethod
        def create(*args, **kwargs):
            return FakeResponse(FakeAnthropicUsage(11, 9))

    class Anthropic:
        def __init__(self):
            self.messages = _Messages()

    module.messages = _Messages()
    module.Anthropic = Anthropic
    sys.modules["anthropic"] = module
    return module


def _install_fake_requests():
    module = types.ModuleType("requests")

    class Session:
        def request(self, method, url, *args, **kwargs):
            return FakeRequestsResponse(status_code=201)

    sessions = types.ModuleType("requests.sessions")
    sessions.Session = Session
    module.sessions = sessions
    sys.modules["requests"] = module
    sys.modules["requests.sessions"] = sessions
    return module


def test_openai_patching(monkeypatch):
    fake_openai = _install_fake_openai()
    tracer = FakeTracer()
    monkeypatch.setattr("agent_lighthouse.auto.get_tracer", lambda: tracer)

    import agent_lighthouse.auto as auto
    auto.instrument()

    resp = fake_openai.ChatCompletion.create(model="gpt-4")
    assert resp.usage.prompt_tokens == 10
    assert tracer.trace_calls == 1
    assert tracer.span_calls == 1
    assert tracer.tokens


def test_anthropic_patching(monkeypatch):
    fake_anthropic = _install_fake_anthropic()
    tracer = FakeTracer()
    monkeypatch.setattr("agent_lighthouse.auto.get_tracer", lambda: tracer)

    import agent_lighthouse.auto as auto
    auto.instrument()

    resp = fake_anthropic.messages.create(model="claude-3-sonnet")
    assert resp.usage.input_tokens == 11
    assert tracer.trace_calls == 1
    assert tracer.span_calls == 1
    assert tracer.tokens


def test_requests_allowlist(monkeypatch):
    _install_fake_requests()
    tracer = FakeTracer()
    monkeypatch.setattr("agent_lighthouse.auto.get_tracer", lambda: tracer)

    import agent_lighthouse.auto as auto
    auto.instrument()

    import requests
    resp = requests.sessions.Session().request("POST", "https://api.openai.com/v1/chat/completions")
    assert resp.status_code == 201
    assert tracer.span_calls == 1
    assert tracer.outputs


def test_capture_policy(monkeypatch):
    _install_fake_openai()
    tracer = FakeTracer()
    monkeypatch.setattr("agent_lighthouse.auto.get_tracer", lambda: tracer)
    monkeypatch.setenv("LIGHTHOUSE_CAPTURE_CONTENT", "true")

    import agent_lighthouse.auto as auto
    auto.instrument()

    import openai
    openai.ChatCompletion.create(model="gpt-4")
    assert tracer.outputs


def test_pricing_override(monkeypatch):
    monkeypatch.setenv(
        "LIGHTHOUSE_PRICING_JSON",
        '{"gpt-4":{"prompt_per_1k":0.5,"completion_per_1k":1.0}}',
    )
    from agent_lighthouse.pricing import get_cost_usd, reset_pricing_cache
    reset_pricing_cache()
    cost = get_cost_usd("gpt-4", 1000, 1000)
    assert cost == pytest.approx(1.5)


def test_idempotent_instrumentation(monkeypatch):
    fake_openai = _install_fake_openai()
    tracer = FakeTracer()
    monkeypatch.setattr("agent_lighthouse.auto.get_tracer", lambda: tracer)

    import agent_lighthouse.auto as auto
    auto.instrument()
    first = fake_openai.ChatCompletion.create
    auto.instrument()
    second = fake_openai.ChatCompletion.create
    assert first is second
