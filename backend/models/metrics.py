"""
Token and cost metrics models
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TokenMetrics(BaseModel):
    """
    Token usage and cost metrics for a single operation
    """
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    # Cost calculation
    cost_per_1k_prompt: float = 0.0
    cost_per_1k_completion: float = 0.0
    total_cost_usd: float = 0.0
    
    # Model info
    model: Optional[str] = None
    
    def calculate_cost(self):
        """Calculate total cost based on token counts and rates"""
        prompt_cost = (self.prompt_tokens / 1000) * self.cost_per_1k_prompt
        completion_cost = (self.completion_tokens / 1000) * self.cost_per_1k_completion
        self.total_cost_usd = prompt_cost + completion_cost
        return self.total_cost_usd


class AgentMetrics(BaseModel):
    """
    Aggregated metrics for a specific agent
    """
    agent_id: str
    agent_name: str
    
    # Token metrics
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    
    # Cost
    total_cost_usd: float = 0.0
    cost_percentage: float = 0.0  # % of total trace cost
    
    # Performance
    invocation_count: int = 0
    avg_tokens_per_call: float = 0.0
    avg_cost_per_call: float = 0.0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    
    # Burn rate (tokens per minute)
    tokens_per_minute: float = 0.0
    cost_per_minute: float = 0.0
    
    # Time window
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    
    def update(self, tokens: int, cost: float, duration_ms: float):
        """Update metrics with a new invocation"""
        self.invocation_count += 1
        self.total_tokens += tokens
        self.total_cost_usd += cost
        self.total_duration_ms += duration_ms
        
        # Update averages
        self.avg_tokens_per_call = self.total_tokens / self.invocation_count
        self.avg_cost_per_call = self.total_cost_usd / self.invocation_count
        self.avg_duration_ms = self.total_duration_ms / self.invocation_count


class TraceMetricsSummary(BaseModel):
    """
    Summary metrics for an entire trace
    """
    trace_id: str
    
    # Totals
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_duration_ms: float = 0.0
    
    # Breakdown by agent
    agent_metrics: list[AgentMetrics] = Field(default_factory=list)
    
    # Breakdown by type
    llm_tokens: int = 0
    llm_cost: float = 0.0
    llm_calls: int = 0
    
    tool_calls: int = 0
    tool_errors: int = 0
    
    # Top consumers
    most_expensive_agent: Optional[str] = None
    most_tokens_agent: Optional[str] = None
    
    def calculate_percentages(self):
        """Calculate cost percentages for each agent"""
        if self.total_cost_usd > 0:
            for am in self.agent_metrics:
                am.cost_percentage = (am.total_cost_usd / self.total_cost_usd) * 100
        
        # Find top consumers
        if self.agent_metrics:
            by_cost = max(self.agent_metrics, key=lambda x: x.total_cost_usd)
            self.most_expensive_agent = by_cost.agent_name
            
            by_tokens = max(self.agent_metrics, key=lambda x: x.total_tokens)
            self.most_tokens_agent = by_tokens.agent_name
