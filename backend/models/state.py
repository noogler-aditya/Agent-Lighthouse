"""
Agent state and execution control models
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field
import uuid
import copy


class ExecutionStatus(str, Enum):
    """Execution control status"""
    RUNNING = "running"
    PAUSED = "paused"
    STEP = "step"  # Execute one step then pause
    STOPPED = "stopped"


class ExecutionControl(BaseModel):
    """
    Controls for pausing/resuming agent execution
    """
    trace_id: str
    status: ExecutionStatus = ExecutionStatus.RUNNING
    
    # Breakpoints
    breakpoint_spans: list[str] = Field(default_factory=list)  # Span IDs to break at
    breakpoint_agents: list[str] = Field(default_factory=list)  # Agent IDs to break at
    
    # Step execution
    step_count: int = 0  # Number of steps to execute before pausing
    current_step: int = 0
    
    # Pause info
    paused_at: Optional[datetime] = None
    paused_span_id: Optional[str] = None
    resume_requested: bool = False
    
    def pause(self, span_id: Optional[str] = None):
        """Pause execution"""
        self.status = ExecutionStatus.PAUSED
        self.paused_at = datetime.utcnow()
        self.paused_span_id = span_id
        self.resume_requested = False
    
    def resume(self):
        """Resume execution"""
        self.status = ExecutionStatus.RUNNING
        self.resume_requested = True
        self.paused_at = None
        self.paused_span_id = None
    
    def step(self, count: int = 1):
        """Execute N steps then pause"""
        self.status = ExecutionStatus.STEP
        self.step_count = count
        self.current_step = 0
        self.resume_requested = True


class StateSnapshot(BaseModel):
    """
    A snapshot of agent state at a point in time
    """
    snapshot_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str
    span_id: str
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # State data (JSON-serializable)
    state_data: dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    description: Optional[str] = None
    
    # User modifications
    is_modified: bool = False
    modified_at: Optional[datetime] = None
    original_state: Optional[dict[str, Any]] = None


class AgentState(BaseModel):
    """
    Complete agent state including memory, context, and execution control
    """
    trace_id: str
    
    # Current state
    current_span_id: Optional[str] = None
    current_agent_id: Optional[str] = None
    
    # Memory/Context
    memory: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    variables: dict[str, Any] = Field(default_factory=dict)
    
    # Message history (for chat-based agents)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    
    # Tool state
    pending_tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: dict[str, Any] = Field(default_factory=dict)
    
    # State history (for time-travel debugging)
    snapshots: list[StateSnapshot] = Field(default_factory=list)
    
    # Execution control
    control: ExecutionControl = Field(default_factory=lambda: ExecutionControl(trace_id=""))
    
    # Timestamps
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    def take_snapshot(self, span_id: str, description: Optional[str] = None) -> StateSnapshot:
        """Create a snapshot of current state"""
        snapshot = StateSnapshot(
            trace_id=self.trace_id,
            span_id=span_id,
            agent_id=self.current_agent_id,
            description=description,
            state_data={
                "memory": copy.deepcopy(self.memory),
                "context": copy.deepcopy(self.context),
                "variables": copy.deepcopy(self.variables),
                "messages": copy.deepcopy(self.messages),
            }
        )
        self.snapshots.append(snapshot)
        return snapshot
    
    def restore_snapshot(self, snapshot_id: str) -> bool:
        """Restore state from a snapshot"""
        for snapshot in self.snapshots:
            if snapshot.snapshot_id == snapshot_id:
                self.memory = snapshot.state_data.get("memory", {})
                self.context = snapshot.state_data.get("context", {})
                self.variables = snapshot.state_data.get("variables", {})
                self.messages = snapshot.state_data.get("messages", [])
                self.last_updated = datetime.utcnow()
                return True
        return False
    
    def modify_state(self, path: str, value: Any):
        """
        Modify state at a given path (e.g., "memory.key" or "variables.x")
        """
        parts = path.split(".")
        if len(parts) < 2:
            return False
        
        container_name = parts[0]
        key_path = parts[1:]
        
        containers = {
            "memory": self.memory,
            "context": self.context,
            "variables": self.variables,
        }
        
        if container_name not in containers:
            return False
        
        container = containers[container_name]
        
        # Navigate to the nested key
        for key in key_path[:-1]:
            if key not in container:
                container[key] = {}
            if not isinstance(container[key], dict):
                return False
            container = container[key]
        
        # Set the value
        container[key_path[-1]] = value
        self.last_updated = datetime.utcnow()
        return True
