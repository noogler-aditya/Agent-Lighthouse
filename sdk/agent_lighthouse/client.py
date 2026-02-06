"""
HTTP Client for Agent Lighthouse API
"""
import httpx
from typing import Optional, Any
from datetime import datetime


class LighthouseClient:
    """
    Sync/Async HTTP client for Agent Lighthouse backend.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None
        self._async_client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout
            )
        return self._client
    
    @property
    def async_client(self) -> httpx.AsyncClient:
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout
            )
        return self._async_client
    
    def close(self):
        if self._client:
            self._client.close()
        if self._async_client:
            import asyncio
            asyncio.get_event_loop().run_until_complete(self._async_client.aclose())
    
    # ============ TRACES ============
    
    def create_trace(
        self,
        name: str,
        description: Optional[str] = None,
        framework: Optional[str] = None,
        metadata: dict = {}
    ) -> dict:
        """Create a new trace"""
        response = self.client.post("/api/traces", json={
            "name": name,
            "description": description,
            "framework": framework,
            "metadata": metadata
        })
        response.raise_for_status()
        return response.json()
    
    def get_trace(self, trace_id: str) -> dict:
        """Get a trace by ID"""
        response = self.client.get(f"/api/traces/{trace_id}")
        response.raise_for_status()
        return response.json()
    
    def list_traces(self, offset: int = 0, limit: int = 50) -> dict:
        """List all traces"""
        response = self.client.get("/api/traces", params={
            "offset": offset,
            "limit": limit
        })
        response.raise_for_status()
        return response.json()
    
    def complete_trace(self, trace_id: str, status: str = "success") -> dict:
        """Mark a trace as complete"""
        response = self.client.post(
            f"/api/traces/{trace_id}/complete",
            params={"status": status}
        )
        response.raise_for_status()
        return response.json()
    
    # ============ SPANS ============
    
    def create_span(
        self,
        trace_id: str,
        name: str,
        kind: str,
        parent_span_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        input_data: Optional[dict] = None,
        attributes: dict = {}
    ) -> dict:
        """Create a new span"""
        response = self.client.post(f"/api/traces/{trace_id}/spans", json={
            "name": name,
            "kind": kind,
            "parent_span_id": parent_span_id,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "input_data": input_data,
            "attributes": attributes
        })
        response.raise_for_status()
        return response.json()
    
    def update_span(
        self,
        trace_id: str,
        span_id: str,
        status: Optional[str] = None,
        output_data: Optional[dict] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        cost_usd: Optional[float] = None,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None
    ) -> dict:
        """Update a span"""
        data = {}
        if status:
            data["status"] = status
        if output_data:
            data["output_data"] = output_data
        if prompt_tokens is not None:
            data["prompt_tokens"] = prompt_tokens
        if completion_tokens is not None:
            data["completion_tokens"] = completion_tokens
        if total_tokens is not None:
            data["total_tokens"] = total_tokens
        if cost_usd is not None:
            data["cost_usd"] = cost_usd
        if error_message:
            data["error_message"] = error_message
            data["error_type"] = error_type
        
        response = self.client.patch(
            f"/api/traces/{trace_id}/spans/{span_id}",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    # ============ STATE ============
    
    def get_state(self, trace_id: str) -> dict:
        """Get state for a trace"""
        response = self.client.get(f"/api/state/{trace_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    
    def update_state(
        self,
        trace_id: str,
        memory: Optional[dict] = None,
        context: Optional[dict] = None,
        variables: Optional[dict] = None
    ) -> dict:
        """Update state"""
        data = {}
        if memory is not None:
            data["memory"] = memory
        if context is not None:
            data["context"] = context
        if variables is not None:
            data["variables"] = variables
        
        response = self.client.put(f"/api/state/{trace_id}", json=data)
        response.raise_for_status()
        return response.json()
    
    def get_control_status(self, trace_id: str) -> dict:
        """Check if execution is paused"""
        response = self.client.get(f"/api/state/{trace_id}/control")
        response.raise_for_status()
        return response.json()
    
    def wait_if_paused(self, trace_id: str, poll_interval: float = 0.5) -> bool:
        """
        Block until execution is resumed.
        Returns True if was paused and now resumed.
        """
        import time
        
        while True:
            status = self.get_control_status(trace_id)
            if status.get("status") == "paused":
                time.sleep(poll_interval)
            elif status.get("resume_requested"):
                return True
            else:
                return False
