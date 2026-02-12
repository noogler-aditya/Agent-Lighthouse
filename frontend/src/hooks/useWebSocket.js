import { useState, useEffect, useCallback, useRef } from 'react';
import { WS_URL } from '../config';
import { getAccessToken, refreshSession } from '../auth/session';

export function useWebSocket(enabled = true) {
    const [isConnected, setIsConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState(null);
    const wsRef = useRef(null);
    const connectRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);
    const shouldReconnectRef = useRef(true);
    const messageHandlersRef = useRef(new Map());

    const connect = useCallback(async () => {
        if (!enabled || wsRef.current?.readyState === WebSocket.OPEN) return;

        let token = await getAccessToken();
        if (!token) {
            try {
                await refreshSession();
                token = await getAccessToken();
            } catch {
                setIsConnected(false);
                return;
            }
        }

        const endpoint = new URL(WS_URL, window.location.origin);
        const ws = new WebSocket(endpoint.toString(), ['bearer', token]);

        ws.onopen = () => {
            setIsConnected(true);
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
                reconnectTimeoutRef.current = null;
            }
        };

        ws.onclose = () => {
            setIsConnected(false);
            wsRef.current = null;
            if (shouldReconnectRef.current) {
                reconnectTimeoutRef.current = setTimeout(() => {
                    connectRef.current?.().catch(() => {});
                }, 3000);
            }
        };

        ws.onerror = () => {
            ws.close();
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                setLastMessage(data);

                // Call registered handlers
                messageHandlersRef.current.forEach((handlers, type) => {
                    if (data.type === type || type === '*') {
                        handlers.forEach((handler) => handler(data));
                    }
                });
            } catch {
                // Ignore malformed payloads
            }
        };

        wsRef.current = ws;
    }, [enabled]);

    useEffect(() => {
        connectRef.current = connect;
    }, [connect]);

    const disconnect = useCallback(() => {
        shouldReconnectRef.current = false;
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
    }, []);

    const send = useCallback((data) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(data));
        }
    }, []);

    const subscribeToTrace = useCallback((traceId) => {
        send({ action: 'subscribe', trace_id: traceId });
    }, [send]);

    const unsubscribeFromTrace = useCallback((traceId) => {
        send({ action: 'unsubscribe', trace_id: traceId });
    }, [send]);

    const onMessage = useCallback((type, handler) => {
        if (!messageHandlersRef.current.has(type)) {
            messageHandlersRef.current.set(type, new Set());
        }
        const typeHandlers = messageHandlersRef.current.get(type);
        typeHandlers.add(handler);

        return () => {
            typeHandlers.delete(handler);
            if (typeHandlers.size === 0) {
                messageHandlersRef.current.delete(type);
            }
        };
    }, []);

    useEffect(() => {
        if (!enabled) {
            disconnect();
            return;
        }
        shouldReconnectRef.current = true;
        const timer = window.setTimeout(() => {
            connectRef.current?.().catch(() => {});
        }, 0);
        return () => {
            window.clearTimeout(timer);
            disconnect();
        };
    }, [connect, disconnect, enabled]);

    return {
        isConnected,
        lastMessage,
        send,
        subscribeToTrace,
        unsubscribeFromTrace,
        onMessage,
    };
}
