"""
State inspection and execution control API router
"""
from typing import Optional, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from dependencies import get_connection_manager, get_redis
from models.state import AgentState, ExecutionControl
from rate_limit import enforce_read_rate_limit, enforce_write_rate_limit
from security import require_auth
from services.connection_manager import ConnectionManager
from services.redis_service import RedisService


router = APIRouter(
    prefix="/api/state",
    tags=["state"],
)


# ============ REQUEST MODELS ============

class InitStateRequest(BaseModel):
    memory: dict = Field(default_factory=dict)
    context: dict = Field(default_factory=dict)
    variables: dict = Field(default_factory=dict)


class ModifyStateRequest(BaseModel):
    path: str  # e.g., "memory.key" or "variables.x.y"
    value: Any


class BulkModifyStateRequest(BaseModel):
    memory: Optional[dict] = None
    context: Optional[dict] = None
    variables: Optional[dict] = None


class StepRequest(BaseModel):
    count: int = Field(default=1, ge=1, le=1000)


class BreakpointRequest(BaseModel):
    span_ids: list[str] = Field(default_factory=list)
    agent_ids: list[str] = Field(default_factory=list)


async def _ensure_trace_exists(trace_id: str, redis: RedisService):
    trace = await redis.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")


# ============ ENDPOINTS ============

@router.get("/{trace_id}")
async def get_state(
    trace_id: str,
    redis: RedisService = Depends(get_redis),
    _auth=Depends(require_auth()),
    _rate=Depends(enforce_read_rate_limit),
):
    """Get current state for a trace"""
    state = await redis.get_state(trace_id)
    if not state:
        raise HTTPException(status_code=404, detail="State not found")
    return state


@router.post("/{trace_id}")
async def initialize_state(
    trace_id: str,
    request: InitStateRequest,
    redis: RedisService = Depends(get_redis),
    _auth=Depends(require_auth()),
    _rate=Depends(enforce_write_rate_limit),
):
    """Initialize state for a trace"""
    # Check trace exists
    trace = await redis.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    state = AgentState(
        trace_id=trace_id,
        memory=request.memory,
        context=request.context,
        variables=request.variables,
        control=ExecutionControl(trace_id=trace_id)
    )
    await redis.save_state(state)
    return state


@router.patch("/{trace_id}")
async def modify_state(
    trace_id: str,
    request: ModifyStateRequest,
    redis: RedisService = Depends(get_redis),
    connection_manager: ConnectionManager = Depends(get_connection_manager),
    _auth=Depends(require_auth()),
    _rate=Depends(enforce_write_rate_limit),
):
    """Modify a specific path in the state"""
    state = await redis.get_state(trace_id)
    if not state:
        raise HTTPException(status_code=404, detail="State not found")
    
    success = state.modify_state(request.path, request.value)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid state path")
    
    await redis.save_state(state)
    
    # Broadcast state change
    await connection_manager.broadcast_state_change(
        trace_id=trace_id,
        control_status=state.control.status.value,
        state_data={
            "memory": state.memory,
            "context": state.context,
            "variables": state.variables
        }
    )
    
    return {"message": "State modified", "path": request.path}


@router.put("/{trace_id}")
async def bulk_modify_state(
    trace_id: str,
    request: BulkModifyStateRequest,
    redis: RedisService = Depends(get_redis),
    connection_manager: ConnectionManager = Depends(get_connection_manager),
    _auth=Depends(require_auth()),
    _rate=Depends(enforce_write_rate_limit),
):
    """Bulk modify state containers"""
    state = await redis.get_state(trace_id)
    if not state:
        raise HTTPException(status_code=404, detail="State not found")
    
    if request.memory is not None:
        state.memory = request.memory
    if request.context is not None:
        state.context = request.context
    if request.variables is not None:
        state.variables = request.variables
    
    await redis.save_state(state)
    
    # Broadcast state change
    await connection_manager.broadcast_state_change(
        trace_id=trace_id,
        control_status=state.control.status.value,
        state_data={
            "memory": state.memory,
            "context": state.context,
            "variables": state.variables
        }
    )
    
    return state


# ============ EXECUTION CONTROL ============

@router.post("/{trace_id}/pause")
async def pause_execution(
    trace_id: str,
    span_id: Optional[str] = None,
    redis: RedisService = Depends(get_redis),
    connection_manager: ConnectionManager = Depends(get_connection_manager),
    _auth=Depends(require_auth()),
    _rate=Depends(enforce_write_rate_limit),
):
    """Pause execution at the current point"""
    await _ensure_trace_exists(trace_id, redis)
    state = await redis.get_state(trace_id)
    if not state:
        # Create state if it doesn't exist
        state = AgentState(
            trace_id=trace_id,
            control=ExecutionControl(trace_id=trace_id)
        )
    
    state.control.pause(span_id)
    await redis.save_state(state)
    
    # Broadcast pause event
    await connection_manager.broadcast_state_change(
        trace_id=trace_id,
        control_status="paused"
    )
    
    return {"message": "Execution paused", "status": "paused"}


@router.post("/{trace_id}/resume")
async def resume_execution(
    trace_id: str,
    redis: RedisService = Depends(get_redis),
    connection_manager: ConnectionManager = Depends(get_connection_manager),
    _auth=Depends(require_auth()),
    _rate=Depends(enforce_write_rate_limit),
):
    """Resume paused execution"""
    state = await redis.get_state(trace_id)
    if not state:
        raise HTTPException(status_code=404, detail="State not found")
    
    state.control.resume()
    await redis.save_state(state)
    
    # Broadcast resume event
    await connection_manager.broadcast_state_change(
        trace_id=trace_id,
        control_status="running"
    )
    
    return {"message": "Execution resumed", "status": "running"}


@router.post("/{trace_id}/step")
async def step_execution(
    trace_id: str,
    request: StepRequest,
    redis: RedisService = Depends(get_redis),
    connection_manager: ConnectionManager = Depends(get_connection_manager),
    _auth=Depends(require_auth()),
    _rate=Depends(enforce_write_rate_limit),
):
    """Execute N steps then pause"""
    state = await redis.get_state(trace_id)
    if not state:
        raise HTTPException(status_code=404, detail="State not found")
    
    state.control.step(request.count)
    await redis.save_state(state)

    await connection_manager.broadcast_state_change(
        trace_id=trace_id,
        control_status="step",
    )

    return {"message": f"Stepping {request.count} step(s)", "status": "step"}


@router.get("/{trace_id}/control")
async def get_control_status(
    trace_id: str,
    redis: RedisService = Depends(get_redis),
    _auth=Depends(require_auth()),
    _rate=Depends(enforce_read_rate_limit),
):
    """Get current execution control status"""
    state = await redis.get_state(trace_id)
    if not state:
        return {"status": "unknown", "trace_id": trace_id}
    
    return {
        "trace_id": trace_id,
        "status": state.control.status.value,
        "paused_at": state.control.paused_at.isoformat() if state.control.paused_at else None,
        "paused_span_id": state.control.paused_span_id,
        "resume_requested": state.control.resume_requested
    }


# ============ BREAKPOINTS ============

@router.post("/{trace_id}/breakpoints")
async def set_breakpoints(
    trace_id: str,
    request: BreakpointRequest,
    redis: RedisService = Depends(get_redis),
    _auth=Depends(require_auth()),
    _rate=Depends(enforce_write_rate_limit),
):
    """Set breakpoints for debugging"""
    await _ensure_trace_exists(trace_id, redis)
    state = await redis.get_state(trace_id)
    if not state:
        state = AgentState(
            trace_id=trace_id,
            control=ExecutionControl(trace_id=trace_id)
        )
    
    state.control.breakpoint_spans = request.span_ids
    state.control.breakpoint_agents = request.agent_ids
    await redis.save_state(state)
    
    return {
        "message": "Breakpoints set",
        "span_breakpoints": request.span_ids,
        "agent_breakpoints": request.agent_ids
    }


# ============ SNAPSHOTS ============

@router.post("/{trace_id}/snapshot")
async def take_snapshot(
    trace_id: str,
    span_id: str,
    description: Optional[str] = None,
    redis: RedisService = Depends(get_redis),
    _auth=Depends(require_auth()),
    _rate=Depends(enforce_write_rate_limit),
):
    """Take a snapshot of current state"""
    state = await redis.get_state(trace_id)
    if not state:
        raise HTTPException(status_code=404, detail="State not found")
    
    snapshot = state.take_snapshot(span_id, description)
    await redis.save_state(state)
    
    return snapshot


@router.get("/{trace_id}/snapshots")
async def list_snapshots(
    trace_id: str,
    redis: RedisService = Depends(get_redis),
    _auth=Depends(require_auth()),
    _rate=Depends(enforce_read_rate_limit),
):
    """List all state snapshots for a trace"""
    state = await redis.get_state(trace_id)
    if not state:
        raise HTTPException(status_code=404, detail="State not found")
    
    return {"snapshots": state.snapshots}


@router.post("/{trace_id}/snapshots/{snapshot_id}/restore")
async def restore_snapshot(
    trace_id: str,
    snapshot_id: str,
    redis: RedisService = Depends(get_redis),
    connection_manager: ConnectionManager = Depends(get_connection_manager),
    _auth=Depends(require_auth()),
    _rate=Depends(enforce_write_rate_limit),
):
    """Restore state from a snapshot"""
    state = await redis.get_state(trace_id)
    if not state:
        raise HTTPException(status_code=404, detail="State not found")
    
    success = state.restore_snapshot(snapshot_id)
    if not success:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    await redis.save_state(state)
    
    # Broadcast state change
    await connection_manager.broadcast_state_change(
        trace_id=trace_id,
        control_status=state.control.status.value,
        state_data={
            "memory": state.memory,
            "context": state.context,
            "variables": state.variables
        }
    )
    
    return {"message": "State restored from snapshot"}
