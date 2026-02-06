"""
Traces API router
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from models.trace import Trace, Span, SpanKind, SpanStatus
from services.redis_service import RedisService


router = APIRouter(prefix="/api/traces", tags=["traces"])


# Dependency to get Redis service
async def get_redis() -> RedisService:
    from main import redis_service
    return redis_service


# ============ REQUEST/RESPONSE MODELS ============

class CreateTraceRequest(BaseModel):
    name: str
    description: Optional[str] = None
    framework: Optional[str] = None
    metadata: dict = {}


class CreateSpanRequest(BaseModel):
    name: str
    kind: SpanKind
    parent_span_id: Optional[str] = None
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    input_data: Optional[dict] = None
    attributes: dict = {}


class UpdateSpanRequest(BaseModel):
    status: Optional[SpanStatus] = None
    output_data: Optional[dict] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None


class TraceListResponse(BaseModel):
    traces: list[Trace]
    total: int
    offset: int
    limit: int


# ============ ENDPOINTS ============

@router.get("", response_model=TraceListResponse)
async def list_traces(
    offset: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    redis: RedisService = Depends(get_redis)
):
    """List all traces with pagination"""
    traces = await redis.list_traces(offset=offset, limit=limit, status=status)
    return TraceListResponse(
        traces=traces,
        total=len(traces),  # TODO: Get actual total count
        offset=offset,
        limit=limit
    )


@router.post("", response_model=Trace)
async def create_trace(
    request: CreateTraceRequest,
    redis: RedisService = Depends(get_redis)
):
    """Create a new trace"""
    trace = Trace(
        name=request.name,
        description=request.description,
        framework=request.framework,
        metadata=request.metadata
    )
    await redis.save_trace(trace)
    return trace


@router.get("/{trace_id}", response_model=Trace)
async def get_trace(
    trace_id: str,
    redis: RedisService = Depends(get_redis)
):
    """Get a trace by ID"""
    trace = await redis.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


@router.delete("/{trace_id}")
async def delete_trace(
    trace_id: str,
    redis: RedisService = Depends(get_redis)
):
    """Delete a trace"""
    await redis.delete_trace(trace_id)
    return {"message": "Trace deleted"}


@router.post("/{trace_id}/complete")
async def complete_trace(
    trace_id: str,
    status: SpanStatus = SpanStatus.SUCCESS,
    redis: RedisService = Depends(get_redis)
):
    """Mark a trace as complete"""
    trace = await redis.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    trace.complete(status)
    await redis.update_trace(trace)
    return trace


@router.get("/{trace_id}/tree")
async def get_trace_tree(
    trace_id: str,
    redis: RedisService = Depends(get_redis)
):
    """Get trace as a hierarchical tree structure for visualization"""
    trace = await redis.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    return {
        "trace_id": trace_id,
        "name": trace.name,
        "tree": trace.get_span_tree()
    }


# ============ SPAN ENDPOINTS ============

@router.post("/{trace_id}/spans", response_model=Span)
async def create_span(
    trace_id: str,
    request: CreateSpanRequest,
    redis: RedisService = Depends(get_redis)
):
    """Add a span to a trace"""
    trace = await redis.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    span = Span(
        trace_id=trace_id,
        name=request.name,
        kind=request.kind,
        parent_span_id=request.parent_span_id,
        agent_id=request.agent_id,
        agent_name=request.agent_name,
        input_data=request.input_data,
        attributes=request.attributes
    )
    
    await redis.add_span(span)
    
    # Broadcast to WebSocket clients
    from main import connection_manager
    await connection_manager.broadcast_span_event(
        trace_id=trace_id,
        span_id=span.span_id,
        event_type="span_created",
        data=span.model_dump()
    )
    
    return span


@router.patch("/{trace_id}/spans/{span_id}", response_model=Span)
async def update_span(
    trace_id: str,
    span_id: str,
    request: UpdateSpanRequest,
    redis: RedisService = Depends(get_redis)
):
    """Update a span"""
    trace = await redis.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    # Find the span
    span = None
    for s in trace.spans:
        if s.span_id == span_id:
            span = s
            break
    
    if not span:
        raise HTTPException(status_code=404, detail="Span not found")
    
    # Update fields
    if request.status:
        span.status = request.status
        if request.status in [SpanStatus.SUCCESS, SpanStatus.ERROR]:
            span.complete(request.status, request.output_data)
    if request.output_data:
        span.output_data = request.output_data
    if request.prompt_tokens is not None:
        span.prompt_tokens = request.prompt_tokens
    if request.completion_tokens is not None:
        span.completion_tokens = request.completion_tokens
    if request.total_tokens is not None:
        span.total_tokens = request.total_tokens
    if request.cost_usd is not None:
        span.cost_usd = request.cost_usd
    if request.error_message:
        span.error_message = request.error_message
        span.error_type = request.error_type
    
    await redis.update_span(trace_id, span)
    
    # Broadcast update
    from main import connection_manager
    await connection_manager.broadcast_span_event(
        trace_id=trace_id,
        span_id=span_id,
        event_type="span_updated",
        data=span.model_dump()
    )
    
    return span


@router.get("/{trace_id}/metrics")
async def get_trace_metrics(
    trace_id: str,
    redis: RedisService = Depends(get_redis)
):
    """Get metrics summary for a trace"""
    metrics = await redis.get_metrics_summary(trace_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Trace not found")
    return metrics
