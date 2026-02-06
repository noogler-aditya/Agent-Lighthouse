"""
Trace and Span models for execution tracking
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field
import uuid


class SpanKind(str, Enum):
    """Type of span in the trace"""
    AGENT = "agent"
    TOOL = "tool"
    LLM = "llm"
    CHAIN = "chain"
    RETRIEVER = "retriever"
    INTERNAL = "internal"


class SpanStatus(str, Enum):
    """Status of a span"""
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"


class Span(BaseModel):
    """
    A single operation within a trace.
    Represents an agent action, tool call, or LLM request.
    """
    span_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_span_id: Optional[str] = None
    trace_id: str
    
    name: str
    kind: SpanKind
    status: SpanStatus = SpanStatus.RUNNING
    
    # Timing
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    
    # Agent/Tool info
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    
    # Input/Output
    input_data: Optional[dict[str, Any]] = None
    output_data: Optional[dict[str, Any]] = None
    
    # Token metrics
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    
    # Error tracking
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    
    # Metadata
    attributes: dict[str, Any] = Field(default_factory=dict)
    
    def complete(self, status: SpanStatus = SpanStatus.SUCCESS, output: Optional[dict] = None):
        """Mark span as complete"""
        self.end_time = datetime.utcnow()
        self.status = status
        if output:
            self.output_data = output
        if self.start_time and self.end_time:
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000


class Trace(BaseModel):
    """
    A complete execution trace containing multiple spans.
    Represents an entire agent workflow run.
    """
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    name: str
    description: Optional[str] = None
    
    # Status
    status: SpanStatus = SpanStatus.RUNNING
    
    # Timing
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    
    # Spans (flattened list - tree structure derived from parent_span_id)
    spans: list[Span] = Field(default_factory=list)
    root_span_id: Optional[str] = None
    
    # Aggregate metrics
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    agent_count: int = 0
    tool_calls: int = 0
    llm_calls: int = 0
    
    # Metadata
    framework: Optional[str] = None  # e.g., "crewai", "langgraph"
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    def add_span(self, span: Span):
        """Add a span to the trace and update metrics"""
        self.spans.append(span)
        self.total_tokens += span.total_tokens
        self.total_cost_usd += span.cost_usd
        
        if span.kind == SpanKind.AGENT:
            self.agent_count += 1
        elif span.kind == SpanKind.TOOL:
            self.tool_calls += 1
        elif span.kind == SpanKind.LLM:
            self.llm_calls += 1
            
        if not self.root_span_id and span.parent_span_id is None:
            self.root_span_id = span.span_id
    
    def complete(self, status: SpanStatus = SpanStatus.SUCCESS):
        """Mark trace as complete"""
        self.end_time = datetime.utcnow()
        self.status = status
        if self.start_time and self.end_time:
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
    
    def get_span_tree(self) -> dict:
        """Build hierarchical span tree for visualization"""
        spans_by_id = {s.span_id: s for s in self.spans}
        children: dict[str, list[str]] = {s.span_id: [] for s in self.spans}
        
        for span in self.spans:
            if span.parent_span_id and span.parent_span_id in children:
                children[span.parent_span_id].append(span.span_id)
        
        def build_tree(span_id: str) -> dict:
            span = spans_by_id[span_id]
            return {
                "span": span.model_dump(),
                "children": [build_tree(cid) for cid in children[span_id]]
            }
        
        if self.root_span_id:
            return build_tree(self.root_span_id)
        return {}
