import { useState, useEffect, useCallback, useRef } from 'react';
import { API_KEY, WS_URL } from '../config';

export function useWebSocket() {
    const [isConnected, setIsConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState(null);
    const wsRef = useRef(null);
    const connectRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);
    const shouldReconnectRef = useRef(true);
    const messageHandlersRef = useRef(new Map());

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        const endpoint = new URL(WS_URL, window.location.origin);
        if (API_KEY) {
            endpoint.searchParams.set('api_key', API_KEY);
        }
        const ws = new WebSocket(endpoint.toString());

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
                    connectRef.current?.();
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
    }, []);

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
        shouldReconnectRef.current = true;
        connect();
        return disconnect;
    }, [connect, disconnect]);

    return {
        isConnected,
        lastMessage,
        send,
        subscribeToTrace,
        unsubscribeFromTrace,
        onMessage,
    };
}
