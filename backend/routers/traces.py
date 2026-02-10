"""
Traces API router — enterprise-grade with batch ingestion, search, and export.
"""
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from models.trace import Trace, Span, SpanKind, SpanStatus
from dependencies import get_redis, get_connection_manager
from rate_limit import enforce_read_rate_limit, enforce_write_rate_limit
from security import require_auth, require_user_or_machine
from services.connection_manager import ConnectionManager
from services.redis_service import RedisService


router = APIRouter(
    prefix="/api/traces",
    tags=["traces"],
)


# ============ REQUEST/RESPONSE MODELS ============

class CreateTraceRequest(BaseModel):
    name: str
    description: Optional[str] = None
    framework: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class CreateSpanRequest(BaseModel):
    name: str
    kind: SpanKind
    parent_span_id: Optional[str] = None
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    input_data: Optional[dict] = None
    attributes: dict = Field(default_factory=dict)


class UpdateSpanRequest(BaseModel):
    status: Optional[SpanStatus] = None
    output_data: Optional[dict] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    duration_ms: Optional[float] = None  # client-side timing


class BatchCreateSpansRequest(BaseModel):
    """Batch span ingestion — reduces HTTP overhead for high-throughput agents."""
    spans: list[CreateSpanRequest] = Field(..., max_length=100)


class TraceListResponse(BaseModel):
    traces: list[Trace]
    total: int
    offset: int
    limit: int


# ============ ENDPOINTS ============

@router.get("", response_model=TraceListResponse)
async def list_traces(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    status: Optional[str] = Query(default=None, description="Filter by status: running, success, error, cancelled"),
    search: Optional[str] = Query(default=None, description="Search traces by name (case-insensitive)"),
    framework: Optional[str] = Query(default=None, description="Filter by framework: crewai, langgraph, etc."),
    min_cost: Optional[float] = Query(default=None, ge=0, description="Minimum cost in USD"),
    redis: RedisService = Depends(get_redis),
    _auth=Depends(require_user_or_machine("trace:read")),
    _rate=Depends(enforce_read_rate_limit),
):
    """List all traces with pagination, search, and filtering."""
    traces = await redis.list_traces(offset=0, limit=500, status=status)

    # Apply additional filters
    if search:
        search_lower = search.lower()
        traces = [t for t in traces if search_lower in t.name.lower()]
    if framework:
        framework_lower = framework.lower()
        traces = [t for t in traces if t.framework and framework_lower in t.framework.lower()]
    if min_cost is not None:
        traces = [t for t in traces if t.total_cost_usd >= min_cost]

    total = len(traces)
    paginated = traces[offset:offset + limit]

    return TraceListResponse(
        traces=paginated,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("", response_model=Trace)
async def create_trace(
    request: CreateTraceRequest,
    redis: RedisService = Depends(get_redis),
    _auth=Depends(require_user_or_machine("trace:write")),
    _rate=Depends(enforce_write_rate_limit),
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
    redis: RedisService = Depends(get_redis),
    _auth=Depends(require_user_or_machine("trace:read")),
    _rate=Depends(enforce_read_rate_limit),
):
    """Get a trace by ID"""
    trace = await redis.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


@router.delete("/{trace_id}")
async def delete_trace(
    trace_id: str,
    redis: RedisService = Depends(get_redis),
    _auth=Depends(require_auth()),
    _rate=Depends(enforce_write_rate_limit),
):
    """Delete a trace"""
    await redis.delete_trace(trace_id)
    return {"message": "Trace deleted"}


@router.post("/{trace_id}/complete")
async def complete_trace(
    trace_id: str,
    status: SpanStatus = SpanStatus.SUCCESS,
    redis: RedisService = Depends(get_redis),
    _auth=Depends(require_user_or_machine("trace:write")),
    _rate=Depends(enforce_write_rate_limit),
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
    redis: RedisService = Depends(get_redis),
    _auth=Depends(require_user_or_machine("trace:read")),
    _rate=Depends(enforce_read_rate_limit),
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


# ============ EXPORT ENDPOINT ============

@router.get("/{trace_id}/export")
async def export_trace(
    trace_id: str,
    redis: RedisService = Depends(get_redis),
    _auth=Depends(require_user_or_machine("trace:read")),
    _rate=Depends(enforce_read_rate_limit),
):
    """
    Export a trace as downloadable JSON.
    Includes all spans, metadata, and metrics for archival or sharing.
    """
    trace = await redis.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")

    # Get metrics if available
    metrics = await redis.get_metrics_summary(trace_id)
    state = await redis.get_state(trace_id)

    export_data = {
        "version": "1.0",
        "exported_from": "agent-lighthouse",
        "trace": trace.model_dump(mode="json"),
        "metrics": metrics.model_dump(mode="json") if metrics else None,
        "state": state.model_dump(mode="json") if state else None,
    }

    content = json.dumps(export_data, indent=2, default=str)
    filename = f"trace-{trace_id[:8]}-{trace.name.replace(' ', '_')[:30]}.json"

    return StreamingResponse(
        iter([content]),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ============ SPAN ENDPOINTS ============

@router.post("/{trace_id}/spans", response_model=Span)
async def create_span(
    trace_id: str,
    request: CreateSpanRequest,
    redis: RedisService = Depends(get_redis),
    connection_manager: ConnectionManager = Depends(get_connection_manager),
    _auth=Depends(require_user_or_machine("trace:write")),
    _rate=Depends(enforce_write_rate_limit),
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

    updated = await redis.add_span(span)
    if not updated:
        raise HTTPException(status_code=404, detail="Trace not found")

    # Broadcast to WebSocket clients
    await connection_manager.broadcast_span_event(
        trace_id=trace_id,
        span_id=span.span_id,
        event_type="span_created",
        data=span.model_dump(mode="json"),
    )

    return span


@router.post("/{trace_id}/spans/batch")
async def batch_create_spans(
    trace_id: str,
    request: BatchCreateSpansRequest,
    redis: RedisService = Depends(get_redis),
    connection_manager: ConnectionManager = Depends(get_connection_manager),
    _auth=Depends(require_user_or_machine("trace:write")),
    _rate=Depends(enforce_write_rate_limit),
):
    """
    Batch create multiple spans in a single request.
    Reduces HTTP overhead for high-throughput agent systems.
    Accepts up to 100 spans per request.
    """
    trace = await redis.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")

    created_spans = []
    for span_req in request.spans:
        span = Span(
            trace_id=trace_id,
            name=span_req.name,
            kind=span_req.kind,
            parent_span_id=span_req.parent_span_id,
            agent_id=span_req.agent_id,
            agent_name=span_req.agent_name,
            input_data=span_req.input_data,
            attributes=span_req.attributes,
        )
        await redis.add_span(span)
        created_spans.append(span)

        # Broadcast each span creation
        await connection_manager.broadcast_span_event(
            trace_id=trace_id,
            span_id=span.span_id,
            event_type="span_created",
            data=span.model_dump(mode="json"),
        )

    return {
        "created": len(created_spans),
        "spans": [s.model_dump(mode="json") for s in created_spans],
    }


@router.patch("/{trace_id}/spans/{span_id}", response_model=Span)
async def update_span(
    trace_id: str,
    span_id: str,
    request: UpdateSpanRequest,
    redis: RedisService = Depends(get_redis),
    connection_manager: ConnectionManager = Depends(get_connection_manager),
    _auth=Depends(require_user_or_machine("trace:write")),
    _rate=Depends(enforce_write_rate_limit),
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
    if request.duration_ms is not None:
        span.duration_ms = request.duration_ms

    updated = await redis.update_span(trace_id, span)
    if not updated:
        raise HTTPException(status_code=404, detail="Span not found")

    # Broadcast update
    await connection_manager.broadcast_span_event(
        trace_id=trace_id,
        span_id=span_id,
        event_type="span_updated",
        data=span.model_dump(mode="json"),
    )

    return span


@router.get("/{trace_id}/metrics")
async def get_trace_metrics(
    trace_id: str,
    redis: RedisService = Depends(get_redis),
    _auth=Depends(require_user_or_machine("trace:read")),
    _rate=Depends(enforce_read_rate_limit),
):
    """Get metrics summary for a trace"""
    metrics = await redis.get_metrics_summary(trace_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Trace not found")
    return metrics
