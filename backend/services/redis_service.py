"""
Redis service for trace and state persistence
"""
import json
from typing import Optional, Any
from datetime import datetime
import redis.asyncio as redis
from models.trace import Trace, Span
from models.agent import Agent
from models.state import AgentState
from models.metrics import TraceMetricsSummary


class RedisService:
    """
    Async Redis service for Agent Lighthouse.
    Handles trace storage, state persistence, and pub/sub.
    """
    
    # Key prefixes
    TRACE_PREFIX = "lighthouse:trace:"
    SPAN_PREFIX = "lighthouse:span:"
    AGENT_PREFIX = "lighthouse:agent:"
    STATE_PREFIX = "lighthouse:state:"
    METRICS_PREFIX = "lighthouse:metrics:"
    
    # Channels
    TRACE_CHANNEL = "lighthouse:events:traces"
    SPAN_CHANNEL = "lighthouse:events:spans"
    STATE_CHANNEL = "lighthouse:events:state"
    
    def __init__(self, redis_url: str = "redis://localhost:6379", trace_ttl_hours: int = 24):
        self.redis_url = redis_url
        self.trace_ttl_hours = trace_ttl_hours
        self.redis: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
    
    async def connect(self):
        """Connect to Redis"""
        self.redis = redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        self.pubsub = self.redis.pubsub()
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.pubsub:
            await self.pubsub.aclose()
        if self.redis:
            await self.redis.aclose()
    
    # ============ TRACE OPERATIONS ============
    
    async def save_trace(
        self,
        trace: Trace,
        ttl_hours: Optional[int] = None,
        event_type: Optional[str] = None,
    ) -> bool:
        """Save a trace to Redis"""
        key = f"{self.TRACE_PREFIX}{trace.trace_id}"
        data = trace.model_dump_json()
        exists = await self.redis.exists(key)
        ttl_seconds = (ttl_hours or self.trace_ttl_hours) * 3600
        await self.redis.set(key, data, ex=ttl_seconds)
        
        # Add to traces list (sorted by start time)
        await self.redis.zadd(
            f"{self.TRACE_PREFIX}list",
            {trace.trace_id: trace.start_time.timestamp()}
        )
        
        if event_type is None:
            event_type = "trace_updated" if exists else "trace_created"

        # Publish event
        await self.publish_event(self.TRACE_CHANNEL, {
            "type": event_type,
            "trace_id": trace.trace_id,
            "name": trace.name,
            "status": trace.status.value
        })
        
        return True
    
    async def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get a trace by ID"""
        key = f"{self.TRACE_PREFIX}{trace_id}"
        data = await self.redis.get(key)
        if data:
            return Trace.model_validate_json(data)
        return None
    
    async def list_traces(
        self, 
        offset: int = 0, 
        limit: int = 50,
        status: Optional[str] = None
    ) -> list[Trace]:
        """List traces with pagination (newest first)"""
        # Get trace IDs sorted by time (descending)
        trace_ids = await self.redis.zrevrange(
            f"{self.TRACE_PREFIX}list",
            offset,
            offset + limit - 1
        )
        
        traces = []
        for tid in trace_ids:
            trace = await self.get_trace(tid)
            if trace:
                if status is None or trace.status.value == status:
                    traces.append(trace)
        
        return traces

    async def count_traces(self, status: Optional[str] = None) -> int:
        """Get total count of traces, optionally filtered by status."""
        if status is None:
            return await self.redis.zcard(f"{self.TRACE_PREFIX}list")

        trace_ids = await self.redis.zrange(f"{self.TRACE_PREFIX}list", 0, -1)
        count = 0
        for trace_id in trace_ids:
            trace = await self.get_trace(trace_id)
            if trace and trace.status.value == status:
                count += 1
        return count
    
    async def update_trace(self, trace: Trace) -> bool:
        """Update an existing trace"""
        key = f"{self.TRACE_PREFIX}{trace.trace_id}"
        exists = await self.redis.exists(key)
        if not exists:
            return False
        await self.save_trace(trace, event_type="trace_updated")
        return True
    
    async def delete_trace(self, trace_id: str) -> bool:
        """Delete a trace"""
        key = f"{self.TRACE_PREFIX}{trace_id}"
        await self.redis.delete(key)
        await self.redis.zrem(f"{self.TRACE_PREFIX}list", trace_id)
        
        # Also delete associated state
        await self.delete_state(trace_id)
        
        return True
    
    # ============ SPAN OPERATIONS ============
    
    async def add_span(self, span: Span) -> bool:
        """Add a span to a trace"""
        trace = await self.get_trace(span.trace_id)
        if not trace:
            return False
        
        trace.add_span(span)
        await self.save_trace(trace, event_type="trace_updated")
        
        # Publish span event
        await self.publish_event(self.SPAN_CHANNEL, {
            "type": "span_created",
            "trace_id": span.trace_id,
            "span_id": span.span_id,
            "name": span.name,
            "kind": span.kind.value,
            "status": span.status.value,
            "agent_name": span.agent_name
        })
        
        return True
    
    async def update_span(self, trace_id: str, span: Span) -> bool:
        """Update a span within a trace"""
        trace = await self.get_trace(trace_id)
        if not trace:
            return False

        found = False
        for i, s in enumerate(trace.spans):
            if s.span_id == span.span_id:
                trace.spans[i] = span
                found = True
                break

        if not found:
            return False

        trace.recalculate_aggregates()
        await self.save_trace(trace, event_type="trace_updated")
        
        # Publish update event
        await self.publish_event(self.SPAN_CHANNEL, {
            "type": "span_updated",
            "trace_id": trace_id,
            "span_id": span.span_id,
            "status": span.status.value
        })
        
        return True
    
    # ============ AGENT OPERATIONS ============
    
    async def save_agent(self, agent: Agent) -> bool:
        """Save agent metadata"""
        key = f"{self.AGENT_PREFIX}{agent.agent_id}"
        await self.redis.set(key, agent.model_dump_json())
        await self.redis.sadd(f"{self.AGENT_PREFIX}set", agent.agent_id)
        return True
    
    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        key = f"{self.AGENT_PREFIX}{agent_id}"
        data = await self.redis.get(key)
        if data:
            return Agent.model_validate_json(data)
        return None
    
    async def list_agents(self) -> list[Agent]:
        """List all known agents"""
        agent_ids = await self.redis.smembers(f"{self.AGENT_PREFIX}set")
        agents = []
        for aid in agent_ids:
            agent = await self.get_agent(aid)
            if agent:
                agents.append(agent)
        return agents
    
    # ============ STATE OPERATIONS ============
    
    async def save_state(self, state: AgentState) -> bool:
        """Save agent state"""
        key = f"{self.STATE_PREFIX}{state.trace_id}"
        state.last_updated = datetime.utcnow()
        await self.redis.set(key, state.model_dump_json())
        
        # Publish state update
        await self.publish_event(self.STATE_CHANNEL, {
            "type": "state_updated",
            "trace_id": state.trace_id,
            "control_status": state.control.status.value
        })
        
        return True
    
    async def get_state(self, trace_id: str) -> Optional[AgentState]:
        """Get state for a trace"""
        key = f"{self.STATE_PREFIX}{trace_id}"
        data = await self.redis.get(key)
        if data:
            return AgentState.model_validate_json(data)
        return None
    
    async def delete_state(self, trace_id: str) -> bool:
        """Delete state for a trace"""
        key = f"{self.STATE_PREFIX}{trace_id}"
        await self.redis.delete(key)
        return True
    
    # ============ PUB/SUB ============
    
    async def publish_event(self, channel: str, data: dict[str, Any]):
        """Publish an event to a channel"""
        await self.redis.publish(channel, json.dumps(data))
    
    async def subscribe(self, *channels: str):
        """Subscribe to channels"""
        await self.pubsub.subscribe(*channels)
    
    async def get_message(self) -> Optional[dict]:
        """Get next message from subscribed channels"""
        message = await self.pubsub.get_message(ignore_subscribe_messages=True)
        if message and message["type"] == "message":
            return json.loads(message["data"])
        return None
    
    # ============ METRICS ============
    
    async def get_metrics_summary(self, trace_id: str) -> Optional[TraceMetricsSummary]:
        """Calculate metrics summary for a trace"""
        trace = await self.get_trace(trace_id)
        if not trace:
            return None
        
        from models.metrics import AgentMetrics
        
        summary = TraceMetricsSummary(
            trace_id=trace_id,
            total_tokens=trace.total_tokens,
            total_cost_usd=trace.total_cost_usd,
            total_duration_ms=trace.duration_ms or 0
        )
        
        # Aggregate by agent
        agent_data: dict[str, AgentMetrics] = {}
        
        for span in trace.spans:
            if span.agent_id:
                if span.agent_id not in agent_data:
                    agent_data[span.agent_id] = AgentMetrics(
                        agent_id=span.agent_id,
                        agent_name=span.agent_name or span.agent_id
                    )
                
                am = agent_data[span.agent_id]
                am.update(
                    tokens=span.total_tokens,
                    cost=span.cost_usd,
                    duration_ms=span.duration_ms or 0
                )
            
            if span.kind.value == "llm":
                summary.llm_tokens += span.total_tokens
                summary.llm_cost += span.cost_usd
                summary.llm_calls += 1
            elif span.kind.value == "tool":
                summary.tool_calls += 1
                if span.status.value == "error":
                    summary.tool_errors += 1
        
        summary.agent_metrics = list(agent_data.values())
        summary.calculate_percentages()
        
        return summary
