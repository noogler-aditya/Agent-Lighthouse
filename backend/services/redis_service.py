"""
Redis service for trace and state persistence.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import redis.asyncio as redis

from models.agent import Agent
from models.metrics import TraceMetricsSummary
from models.state import AgentState
from models.trace import Span, Trace

logger = logging.getLogger(__name__)


class RedisService:
    """
    Async Redis service for Agent Lighthouse.
    Handles trace storage, state persistence, and pub/sub.
    """

    TRACE_PREFIX = "lighthouse:trace:"
    AGENT_PREFIX = "lighthouse:agent:"
    STATE_PREFIX = "lighthouse:state:"

    TRACE_CHANNEL = "lighthouse:events:traces"
    SPAN_CHANNEL = "lighthouse:events:spans"
    STATE_CHANNEL = "lighthouse:events:state"

    def __init__(self, redis_url: str = "redis://localhost:6379", trace_ttl_hours: int = 24):
        self.redis_url = redis_url
        self.trace_ttl_hours = trace_ttl_hours
        self.redis: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None

    async def connect(self):
        """Connect to Redis."""
        self.redis = redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        self.pubsub = self.redis.pubsub()
        await self.redis.ping()

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.pubsub:
            await self.pubsub.aclose()
        if self.redis:
            await self.redis.aclose()

    async def is_ready(self) -> bool:
        if not self.redis:
            return False
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False

    async def verify_persistence_policy(
        self,
        required_appendonly: str,
        required_save: str,
        enforce: bool,
    ):
        """Validate Redis persistence policy expectations."""
        if not self.redis:
            raise RuntimeError("Redis is not initialized")

        appendonly = await self.redis.config_get("appendonly")
        save = await self.redis.config_get("save")

        current_aof = (appendonly.get("appendonly") or "").lower()
        current_save = (save.get("save") or "").strip()

        if required_appendonly and current_aof != required_appendonly.lower():
            message = f"Redis appendonly policy mismatch: expected={required_appendonly}, actual={current_aof}"
            if enforce:
                raise RuntimeError(message)
            logger.warning(message)

        if required_save and current_save != required_save.strip():
            message = f"Redis save policy mismatch: expected='{required_save}', actual='{current_save}'"
            if enforce:
                raise RuntimeError(message)
            logger.warning(message)

    async def save_trace(
        self,
        trace: Trace,
        ttl_hours: Optional[int] = None,
        event_type: Optional[str] = None,
    ) -> bool:
        key = f"{self.TRACE_PREFIX}{trace.trace_id}"
        data = trace.model_dump_json()
        exists = await self.redis.exists(key)
        ttl_seconds = (ttl_hours or self.trace_ttl_hours) * 3600

        await self.redis.set(key, data, ex=ttl_seconds)
        await self.redis.zadd(
            f"{self.TRACE_PREFIX}list",
            {trace.trace_id: trace.start_time.timestamp()},
        )

        if event_type is None:
            event_type = "trace_updated" if exists else "trace_created"

        await self.publish_event(
            self.TRACE_CHANNEL,
            {
                "type": event_type,
                "trace_id": trace.trace_id,
                "name": trace.name,
                "status": trace.status.value,
            },
        )

        return True

    async def get_trace(self, trace_id: str) -> Optional[Trace]:
        key = f"{self.TRACE_PREFIX}{trace_id}"
        data = await self.redis.get(key)
        if data:
            return Trace.model_validate_json(data)
        return None

    async def list_traces(self, offset: int = 0, limit: int = 50, status: Optional[str] = None) -> list[Trace]:
        trace_ids = await self.redis.zrevrange(
            f"{self.TRACE_PREFIX}list",
            offset,
            offset + limit - 1,
        )

        traces = []
        for tid in trace_ids:
            trace = await self.get_trace(tid)
            if trace and (status is None or trace.status.value == status):
                traces.append(trace)

        return traces

    async def count_traces(self, status: Optional[str] = None) -> int:
        """Count traces, optionally filtered by status."""
        if status is None:
            return await self.redis.zcard(f"{self.TRACE_PREFIX}list")

        # Use a cached counter key for status-filtered counts.
        # This is an approximation that avoids O(N) full scans.
        # For exact counts with status filter, we scan but with a pipeline.
        trace_ids = await self.redis.zrange(f"{self.TRACE_PREFIX}list", 0, -1)
        if not trace_ids:
            return 0

        # Use pipeline for batch fetching
        pipe = self.redis.pipeline(transaction=False)
        for tid in trace_ids:
            pipe.get(f"{self.TRACE_PREFIX}{tid}")
        results = await pipe.execute()

        count = 0
        for data in results:
            if data:
                try:
                    trace = Trace.model_validate_json(data)
                    if trace.status.value == status:
                        count += 1
                except Exception:
                    continue
        return count

    async def update_trace(self, trace: Trace) -> bool:
        key = f"{self.TRACE_PREFIX}{trace.trace_id}"
        exists = await self.redis.exists(key)
        if not exists:
            return False
        await self.save_trace(trace, event_type="trace_updated")
        return True

    async def delete_trace(self, trace_id: str) -> bool:
        key = f"{self.TRACE_PREFIX}{trace_id}"
        await self.redis.delete(key)
        await self.redis.zrem(f"{self.TRACE_PREFIX}list", trace_id)
        await self.delete_state(trace_id)
        return True

    async def add_span(self, span: Span) -> bool:
        trace = await self.get_trace(span.trace_id)
        if not trace:
            return False

        trace.add_span(span)
        await self.save_trace(trace, event_type="trace_updated")

        await self.publish_event(
            self.SPAN_CHANNEL,
            {
                "type": "span_created",
                "trace_id": span.trace_id,
                "span_id": span.span_id,
                "name": span.name,
                "kind": span.kind.value,
                "status": span.status.value,
                "agent_name": span.agent_name,
            },
        )

        return True

    async def update_span(self, trace_id: str, span: Span) -> bool:
        trace = await self.get_trace(trace_id)
        if not trace:
            return False

        found = False
        for i, existing in enumerate(trace.spans):
            if existing.span_id == span.span_id:
                trace.spans[i] = span
                found = True
                break

        if not found:
            return False

        trace.recalculate_aggregates()
        await self.save_trace(trace, event_type="trace_updated")

        await self.publish_event(
            self.SPAN_CHANNEL,
            {
                "type": "span_updated",
                "trace_id": trace_id,
                "span_id": span.span_id,
                "status": span.status.value,
            },
        )

        return True

    async def save_agent(self, agent: Agent) -> bool:
        key = f"{self.AGENT_PREFIX}{agent.agent_id}"
        await self.redis.set(key, agent.model_dump_json())
        await self.redis.sadd(f"{self.AGENT_PREFIX}set", agent.agent_id)
        return True

    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        key = f"{self.AGENT_PREFIX}{agent_id}"
        data = await self.redis.get(key)
        if data:
            return Agent.model_validate_json(data)
        return None

    async def list_agents(self) -> list[Agent]:
        agent_ids = await self.redis.smembers(f"{self.AGENT_PREFIX}set")
        agents = []
        for aid in agent_ids:
            agent = await self.get_agent(aid)
            if agent:
                agents.append(agent)
        return agents

    async def save_state(self, state: AgentState) -> bool:
        key = f"{self.STATE_PREFIX}{state.trace_id}"
        state.last_updated = datetime.now(timezone.utc)
        await self.redis.set(key, state.model_dump_json())

        await self.publish_event(
            self.STATE_CHANNEL,
            {
                "type": "state_updated",
                "trace_id": state.trace_id,
                "control_status": state.control.status.value,
            },
        )

        return True

    async def get_state(self, trace_id: str) -> Optional[AgentState]:
        key = f"{self.STATE_PREFIX}{trace_id}"
        data = await self.redis.get(key)
        if data:
            return AgentState.model_validate_json(data)
        return None

    async def delete_state(self, trace_id: str) -> bool:
        key = f"{self.STATE_PREFIX}{trace_id}"
        await self.redis.delete(key)
        return True

    async def publish_event(self, channel: str, data: dict[str, Any]):
        await self.redis.publish(channel, json.dumps(data))

    async def subscribe(self, *channels: str):
        await self.pubsub.subscribe(*channels)

    async def get_message(self) -> Optional[dict]:
        message = await self.pubsub.get_message(ignore_subscribe_messages=True)
        if message and message["type"] == "message":
            return json.loads(message["data"])
        return None

    async def get_metrics_summary(self, trace_id: str) -> Optional[TraceMetricsSummary]:
        trace = await self.get_trace(trace_id)
        if not trace:
            return None

        from models.metrics import AgentMetrics

        summary = TraceMetricsSummary(
            trace_id=trace_id,
            total_tokens=trace.total_tokens,
            total_cost_usd=trace.total_cost_usd,
            total_duration_ms=trace.duration_ms or 0,
        )

        agent_data: dict[str, AgentMetrics] = {}

        for span in trace.spans:
            if span.agent_id:
                if span.agent_id not in agent_data:
                    agent_data[span.agent_id] = AgentMetrics(
                        agent_id=span.agent_id,
                        agent_name=span.agent_name or span.agent_id,
                    )

                am = agent_data[span.agent_id]
                am.update(
                    tokens=span.total_tokens,
                    cost=span.cost_usd,
                    duration_ms=span.duration_ms or 0,
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
