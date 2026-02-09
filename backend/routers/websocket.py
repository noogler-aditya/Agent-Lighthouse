"""
WebSocket router for real-time updates
"""
import json
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from rate_limit import enforce_ws_connect_limit_for_subject, enforce_ws_subscribe_limit_for_subject
from security import AuthError
from security import authenticate_websocket


router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for real-time updates.
    
    Clients can send JSON messages to:
    - Subscribe to specific traces: {"action": "subscribe", "trace_id": "xxx"}
    - Unsubscribe from traces: {"action": "unsubscribe", "trace_id": "xxx"}
    - Ping: {"action": "ping"}
    """
    try:
        principal = await authenticate_websocket(websocket, minimum_role="viewer")
        await enforce_ws_connect_limit_for_subject(websocket, principal.subject)
    except AuthError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
        return
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Rate limit exceeded")
        return

    manager = websocket.app.state.connection_manager
    await manager.connect(websocket, subprotocol="bearer")
    
    try:
        # Send initial connection acknowledgment
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to Agent Lighthouse"
        })
        
        while True:
            # Receive and process messages
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                action = message.get("action")
                
                if action == "subscribe":
                    trace_id = message.get("trace_id")
                    if trace_id:
                        try:
                            await enforce_ws_subscribe_limit_for_subject(websocket, principal.subject)
                        except HTTPException:
                            await websocket.send_json({
                                "type": "error",
                                "message": "Rate limit exceeded for subscriptions",
                            })
                            continue
                        manager.subscribe_to_trace(websocket, trace_id)
                        await websocket.send_json({
                            "type": "subscribed",
                            "trace_id": trace_id
                        })
                
                elif action == "unsubscribe":
                    trace_id = message.get("trace_id")
                    if trace_id:
                        manager.unsubscribe_from_trace(websocket, trace_id)
                        await websocket.send_json({
                            "type": "unsubscribed",
                            "trace_id": trace_id
                        })
                
                elif action == "ping":
                    await websocket.send_json({"type": "pong"})
                
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown action: {action}"
                    })
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/ws/trace/{trace_id}")
async def trace_websocket(websocket: WebSocket, trace_id: str):
    """
    WebSocket endpoint for a specific trace.
    Automatically subscribes to updates for the given trace.
    """
    try:
        principal = await authenticate_websocket(websocket, minimum_role="viewer")
        await enforce_ws_connect_limit_for_subject(websocket, principal.subject)
    except AuthError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
        return
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Rate limit exceeded")
        return

    manager = websocket.app.state.connection_manager
    await manager.connect(websocket, subprotocol="bearer")
    try:
        await enforce_ws_subscribe_limit_for_subject(websocket, principal.subject)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Rate limit exceeded")
        return
    manager.subscribe_to_trace(websocket, trace_id)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "trace_id": trace_id,
            "message": f"Subscribed to trace {trace_id}"
        })
        
        while True:
            # Keep connection alive and process any commands
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                action = message.get("action")
                
                if action == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
