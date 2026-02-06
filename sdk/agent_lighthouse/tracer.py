"""
Tracer and decorators for instrumenting agent code
"""
import functools
import time
import uuid
from typing import Optional, Callable, Any
from contextlib import contextmanager
from .client import LighthouseClient


class LighthouseTracer:
    """
    Tracer for instrumenting multi-agent systems.
    
    Usage:
        tracer = LighthouseTracer()
        
        with tracer.trace("My Agent Workflow"):
            with tracer.span("Agent 1", kind="agent"):
                # Agent logic
                pass
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        framework: Optional[str] = None,
        auto_pause_check: bool = True
    ):
        self.client = LighthouseClient(base_url=base_url)
        self.framework = framework
        self.auto_pause_check = auto_pause_check
        
        self._current_trace_id: Optional[str] = None
        self._current_span_id: Optional[str] = None
        self._span_stack: list[str] = []
    
    @property
    def trace_id(self) -> Optional[str]:
        return self._current_trace_id
    
    @property
    def span_id(self) -> Optional[str]:
        return self._current_span_id
    
    @contextmanager
    def trace(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: dict = {}
    ):
        """
        Context manager for creating a trace.
        
        with tracer.trace("My Workflow"):
            # All spans created here belong to this trace
            pass
        """
        trace_data = self.client.create_trace(
            name=name,
            description=description,
            framework=self.framework,
            metadata=metadata
        )
        self._current_trace_id = trace_data["trace_id"]
        
        try:
            yield trace_data
            self.client.complete_trace(self._current_trace_id, "success")
        except Exception as e:
            self.client.complete_trace(self._current_trace_id, "error")
            raise
        finally:
            self._current_trace_id = None
            self._span_stack.clear()
    
    @contextmanager
    def span(
        self,
        name: str,
        kind: str = "internal",
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        input_data: Optional[dict] = None,
        attributes: dict = {}
    ):
        """
        Context manager for creating a span within a trace.
        
        with tracer.span("Process Data", kind="tool"):
            # Tool execution
            pass
        """
        if not self._current_trace_id:
            raise RuntimeError("No active trace. Use tracer.trace() first.")
        
        # Check for pause if enabled
        if self.auto_pause_check:
            self.client.wait_if_paused(self._current_trace_id)
        
        parent_span_id = self._span_stack[-1] if self._span_stack else None
        
        span_data = self.client.create_span(
            trace_id=self._current_trace_id,
            name=name,
            kind=kind,
            parent_span_id=parent_span_id,
            agent_id=agent_id,
            agent_name=agent_name,
            input_data=input_data,
            attributes=attributes
        )
        
        span_id = span_data["span_id"]
        self._span_stack.append(span_id)
        self._current_span_id = span_id
        
        start_time = time.time()
        
        try:
            yield span_data
            
            duration_ms = (time.time() - start_time) * 1000
            self.client.update_span(
                trace_id=self._current_trace_id,
                span_id=span_id,
                status="success"
            )
        except Exception as e:
            self.client.update_span(
                trace_id=self._current_trace_id,
                span_id=span_id,
                status="error",
                error_message=str(e),
                error_type=type(e).__name__
            )
            raise
        finally:
            self._span_stack.pop()
            self._current_span_id = self._span_stack[-1] if self._span_stack else None
    
    def record_tokens(
        self,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost_usd: float = 0.0,
        model: Optional[str] = None
    ):
        """Record token usage for the current span"""
        if not self._current_trace_id or not self._current_span_id:
            return
        
        self.client.update_span(
            trace_id=self._current_trace_id,
            span_id=self._current_span_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=cost_usd
        )
    
    def update_state(
        self,
        memory: Optional[dict] = None,
        context: Optional[dict] = None,
        variables: Optional[dict] = None
    ):
        """Update the trace state for inspection"""
        if not self._current_trace_id:
            return
        
        self.client.update_state(
            trace_id=self._current_trace_id,
            memory=memory,
            context=context,
            variables=variables
        )


# Global tracer instance
_global_tracer: Optional[LighthouseTracer] = None


def get_tracer(
    base_url: str = "http://localhost:8000",
    framework: Optional[str] = None
) -> LighthouseTracer:
    """Get or create the global tracer instance"""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = LighthouseTracer(base_url=base_url, framework=framework)
    return _global_tracer


def trace_agent(
    name: Optional[str] = None,
    agent_id: Optional[str] = None
):
    """
    Decorator to trace an agent function.
    
    @trace_agent("Research Agent")
    def research_agent(query):
        # Agent logic
        return result
    """
    def decorator(func: Callable) -> Callable:
        agent_name = name or func.__name__
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            if not tracer.trace_id:
                # No active trace, just run the function
                return func(*args, **kwargs)
            
            with tracer.span(
                name=agent_name,
                kind="agent",
                agent_id=agent_id or str(uuid.uuid4()),
                agent_name=agent_name,
                input_data={"args": str(args)[:500], "kwargs": str(kwargs)[:500]}
            ):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def trace_tool(name: Optional[str] = None):
    """
    Decorator to trace a tool function.
    
    @trace_tool("Web Search")
    def search_web(query):
        # Tool logic
        return results
    """
    def decorator(func: Callable) -> Callable:
        tool_name = name or func.__name__
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            if not tracer.trace_id:
                return func(*args, **kwargs)
            
            with tracer.span(
                name=tool_name,
                kind="tool",
                input_data={"args": str(args)[:500], "kwargs": str(kwargs)[:500]}
            ):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def trace_llm(
    name: str = "LLM Call",
    model: Optional[str] = None,
    cost_per_1k_prompt: float = 0.0,
    cost_per_1k_completion: float = 0.0
):
    """
    Decorator to trace an LLM call.
    
    @trace_llm("GPT-4 Call", model="gpt-4", cost_per_1k_prompt=0.03)
    def call_gpt4(prompt):
        response = openai.chat(...)
        return response
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            if not tracer.trace_id:
                return func(*args, **kwargs)
            
            with tracer.span(
                name=name,
                kind="llm",
                input_data={"args": str(args)[:500]},
                attributes={"model": model} if model else {}
            ):
                result = func(*args, **kwargs)
                
                # Try to extract token usage from result
                if hasattr(result, "usage"):
                    usage = result.usage
                    prompt_tokens = getattr(usage, "prompt_tokens", 0)
                    completion_tokens = getattr(usage, "completion_tokens", 0)
                    
                    cost = (
                        (prompt_tokens / 1000) * cost_per_1k_prompt +
                        (completion_tokens / 1000) * cost_per_1k_completion
                    )
                    
                    tracer.record_tokens(
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        cost_usd=cost,
                        model=model
                    )
                
                return result
        
        return wrapper
    return decorator
