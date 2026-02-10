"""
Agents API router
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from dependencies import get_redis
from models.agent import Agent, AgentStatus
from rate_limit import enforce_read_rate_limit, enforce_write_rate_limit
from security import require_auth
from services.redis_service import RedisService


router = APIRouter(
    prefix="/api/agents",
    tags=["agents"],
)


# ============ REQUEST MODELS ============

class RegisterAgentRequest(BaseModel):
    name: str
    role: Optional[str] = None
    goal: Optional[str] = None
    framework: Optional[str] = None
    agent_type: Optional[str] = None
    tools: list[str] = Field(default_factory=list)
    model: Optional[str] = None
    config: dict = Field(default_factory=dict)


class AgentListResponse(BaseModel):
    agents: list[Agent]
    total: int


# ============ ENDPOINTS ============

@router.get("", response_model=AgentListResponse)
async def list_agents(
    redis: RedisService = Depends(get_redis),
    _auth=Depends(require_auth()),
    _rate=Depends(enforce_read_rate_limit),
):
    """List all registered agents"""
    agents = await redis.list_agents()
    return AgentListResponse(agents=agents, total=len(agents))


@router.post("", response_model=Agent)
async def register_agent(
    request: RegisterAgentRequest,
    redis: RedisService = Depends(get_redis),
    _auth=Depends(require_auth()),
    _rate=Depends(enforce_write_rate_limit),
):
    """Register a new agent"""
    agent = Agent(
        name=request.name,
        role=request.role,
        goal=request.goal,
        framework=request.framework,
        agent_type=request.agent_type,
        tools=request.tools,
        model=request.model,
        config=request.config
    )
    await redis.save_agent(agent)
    return agent


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(
    agent_id: str,
    redis: RedisService = Depends(get_redis),
    _auth=Depends(require_auth()),
    _rate=Depends(enforce_read_rate_limit),
):
    """Get an agent by ID"""
    agent = await redis.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/{agent_id}/metrics")
async def get_agent_metrics(
    agent_id: str,
    redis: RedisService = Depends(get_redis),
    _auth=Depends(require_auth()),
    _rate=Depends(enforce_read_rate_limit),
):
    """Get metrics for a specific agent across all traces"""
    agent = await redis.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {
        "agent_id": agent.agent_id,
        "agent_name": agent.name,
        "total_invocations": agent.total_invocations,
        "total_tokens": agent.total_tokens,
        "total_cost_usd": agent.total_cost_usd,
        "avg_duration_ms": agent.avg_duration_ms,
        "error_count": agent.error_count,
        "error_rate": agent.error_count / max(agent.total_invocations, 1),
        "last_active": agent.last_active.isoformat() if agent.last_active else None
    }


@router.patch("/{agent_id}/status")
async def update_agent_status(
    agent_id: str,
    status: AgentStatus,
    redis: RedisService = Depends(get_redis),
    _auth=Depends(require_auth()),
    _rate=Depends(enforce_write_rate_limit),
):
    """Update agent status"""
    agent = await redis.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent.status = status
    await redis.save_agent(agent)
    return {"message": "Status updated", "status": status.value}
