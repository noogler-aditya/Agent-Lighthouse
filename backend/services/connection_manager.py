"""
WebSocket connection manager for real-time updates
"""
from typing import Any, Optional
from fastapi import WebSocket


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.
    Supports broadcasting to all clients or specific trace subscribers.
    """
    
    def __init__(self):
        # All active connections
        self.active_connections: list[WebSocket] = []
        
        # Trace-specific subscriptions
        self.trace_subscriptions: dict[str, list[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, subprotocol: Optional[str] = None):
        """Accept a new WebSocket connection"""
        await websocket.accept(subprotocol=subprotocol)
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # Remove from all trace subscriptions
        for trace_id in list(self.trace_subscriptions.keys()):
            if websocket in self.trace_subscriptions[trace_id]:
                self.trace_subscriptions[trace_id].remove(websocket)
            if not self.trace_subscriptions[trace_id]:
                del self.trace_subscriptions[trace_id]
    
    def subscribe_to_trace(self, websocket: WebSocket, trace_id: str):
        """Subscribe a connection to trace updates"""
        if trace_id not in self.trace_subscriptions:
            self.trace_subscriptions[trace_id] = []
        if websocket not in self.trace_subscriptions[trace_id]:
            self.trace_subscriptions[trace_id].append(websocket)
    
    def unsubscribe_from_trace(self, websocket: WebSocket, trace_id: str):
        """Unsubscribe a connection from trace updates"""
        if trace_id in self.trace_subscriptions:
            if websocket in self.trace_subscriptions[trace_id]:
                self.trace_subscriptions[trace_id].remove(websocket)
    
    async def send_personal_message(self, message: dict[str, Any], websocket: WebSocket):
        """Send a message to a specific connection"""
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict[str, Any]):
        """Broadcast a message to all connections"""
        disconnected = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)
    
    async def broadcast_to_trace(self, trace_id: str, message: dict[str, Any]):
        """Broadcast a message to all subscribers of a specific trace"""
        if trace_id not in self.trace_subscriptions:
            return
        
        disconnected = []
        for connection in list(self.trace_subscriptions[trace_id]):
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)
    
    async def broadcast_span_event(
        self,
        trace_id: str,
        span_id: str,
        event_type: str,
        data: dict[str, Any]
    ):
        """Broadcast a span event to trace subscribers"""
        message = {
            "type": event_type,
            "trace_id": trace_id,
            "span_id": span_id,
            "data": data,
        }
        await self.broadcast_to_trace(trace_id, message)
    
    async def broadcast_metrics_update(self, trace_id: str, metrics: dict[str, Any]):
        """Broadcast metrics update"""
        message = {
            "type": "metrics_update",
            "trace_id": trace_id,
            "metrics": metrics,
        }
        await self.broadcast_to_trace(trace_id, message)
    
    async def broadcast_state_change(
        self,
        trace_id: str,
        control_status: str,
        state_data: Optional[dict[str, Any]] = None
    ):
        """Broadcast state/control change"""
        message = {
            "type": "state_change",
            "trace_id": trace_id,
            "control_status": control_status,
            "state": state_data,
        }
        await self.broadcast_to_trace(trace_id, message)
