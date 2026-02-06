"""
Agent models for tracking individual agents in multi-agent systems
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field
import uuid


class AgentStatus(str, Enum):
    """Current status of an agent"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class Agent(BaseModel):
    """
    Represents a single agent in a multi-agent system.
    Tracks agent metadata, capabilities, and runtime statistics.
    """
    agent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    role: Optional[str] = None
    goal: Optional[str] = None
    
    # Status
    status: AgentStatus = AgentStatus.IDLE
    
    # Framework info
    framework: Optional[str] = None
    agent_type: Optional[str] = None  # e.g., "CrewAgent", "LangGraphNode"
    
    # Capabilities
    tools: list[str] = Field(default_factory=list)
    model: Optional[str] = None  # e.g., "gpt-4", "claude-3"
    
    # Runtime statistics (aggregated across all traces)
    total_invocations: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    avg_duration_ms: float = 0.0
    error_count: int = 0
    
    # Timing
    last_active: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Metadata
    config: dict[str, Any] = Field(default_factory=dict)
    attributes: dict[str, Any] = Field(default_factory=dict)
    
    def record_invocation(
        self, 
        tokens: int = 0, 
        cost: float = 0.0, 
        duration_ms: float = 0.0,
        error: bool = False
    ):
        """Record a new invocation and update statistics"""
        self.total_invocations += 1
        self.total_tokens += tokens
        self.total_cost_usd += cost
        self.last_active = datetime.utcnow()
        
        if error:
            self.error_count += 1
        
        # Update running average duration
        if self.total_invocations == 1:
            self.avg_duration_ms = duration_ms
        else:
            self.avg_duration_ms = (
                (self.avg_duration_ms * (self.total_invocations - 1) + duration_ms) 
                / self.total_invocations
            )
