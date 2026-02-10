"""
WebSocket router for real-time updates.

Enterprise features:
- Server-initiated heartbeat (ping/pong) to detect dead connections
- Automatic cleanup of stale connections
- Rate-limited subscriptions
"""
import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from rate_limit import enforce_ws_connect_limit_for_subject, enforce_ws_subscribe_limit_for_subject
from security import AuthError
from security import authenticate_websocket

logger = logging.getLogger("agent_lighthouse.websocket")

router = APIRouter(tags=["websocket"])

# Heartbeat interval in seconds
_HEARTBEAT_INTERVAL = 30.0
_HEARTBEAT_TIMEOUT = 10.0


async def _heartbeat_loop(websocket: WebSocket):
    """
    Server-initiated heartbeat loop.
    Sends a ping every _HEARTBEAT_INTERVAL seconds.
    If the client doesn't respond within _HEARTBEAT_TIMEOUT, closes the connection.
    """
    try:
        while True:
            await asyncio.sleep(_HEARTBEAT_INTERVAL)
            try:
                await asyncio.wait_for(
                    websocket.send_json({"type": "ping", "ts": asyncio.get_event_loop().time()}),
                    timeout=_HEARTBEAT_TIMEOUT,
                )
            except (asyncio.TimeoutError, Exception):
                logger.info("Heartbeat failed — closing stale WebSocket connection")
                try:
                    await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                except Exception:
                    pass
                return
    except asyncio.CancelledError:
        return
    except Exception:
        return


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
        principal = await authenticate_websocket(websocket)
        await enforce_ws_connect_limit_for_subject(websocket, principal.subject)
    except AuthError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
        return
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Rate limit exceeded")
        return

    manager = websocket.app.state.connection_manager
    await manager.connect(websocket, subprotocol="bearer")

    # Start heartbeat background task
    heartbeat_task = asyncio.create_task(_heartbeat_loop(websocket))

    try:
        # Send initial connection acknowledgment
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to Agent Lighthouse",
            "heartbeat_interval": _HEARTBEAT_INTERVAL,
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

                elif action == "pong":
                    # Client responding to our heartbeat ping — connection is alive
                    pass

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
        pass
    except Exception as exc:
        logger.debug("WebSocket error: %s", exc)
    finally:
        heartbeat_task.cancel()
        manager.disconnect(websocket)


@router.websocket("/ws/trace/{trace_id}")
async def trace_websocket(websocket: WebSocket, trace_id: str):
    """
    WebSocket endpoint for a specific trace.
    Automatically subscribes to updates for the given trace.
    """
    try:
        principal = await authenticate_websocket(websocket)
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

    # Start heartbeat
    heartbeat_task = asyncio.create_task(_heartbeat_loop(websocket))

    try:
        await websocket.send_json({
            "type": "connected",
            "trace_id": trace_id,
            "message": f"Subscribed to trace {trace_id}",
            "heartbeat_interval": _HEARTBEAT_INTERVAL,
        })

        while True:
            # Keep connection alive and process any commands
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                action = message.get("action")

                if action == "ping":
                    await websocket.send_json({"type": "pong"})
                elif action == "pong":
                    pass  # heartbeat response

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.debug("Trace WebSocket error: %s", exc)
    finally:
        heartbeat_task.cancel()
        manager.disconnect(websocket)
