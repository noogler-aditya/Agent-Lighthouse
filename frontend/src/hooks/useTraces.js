import { useState, useEffect, useCallback } from 'react';
import { API_URL } from '../config';
import { authFetch } from '../auth/session';

function computeTraceTotals(spans = []) {
    return spans.reduce(
        (acc, span) => {
            const kind = span.kind;
            acc.total_tokens += span.total_tokens || 0;
            acc.total_cost_usd += span.cost_usd || 0;
            if (kind === 'agent') acc.agent_count += 1;
            if (kind === 'tool') acc.tool_calls += 1;
            if (kind === 'llm') acc.llm_calls += 1;
            return acc;
        },
        {
            total_tokens: 0,
            total_cost_usd: 0,
            agent_count: 0,
            tool_calls: 0,
            llm_calls: 0,
        },
    );
}

export function useTraces(enabled = true) {
    const [traces, setTraces] = useState([]);
    const [selectedTrace, setSelectedTrace] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [errorCode, setErrorCode] = useState(null);
    const [errorMessage, setErrorMessage] = useState('');
    const [lastFetchAt, setLastFetchAt] = useState(null);

    const clearError = useCallback(() => {
        setError(null);
        setErrorCode(null);
        setErrorMessage('');
    }, []);

    const setStructuredError = useCallback((code, message) => {
        setError(message);
        setErrorCode(code);
        setErrorMessage(message);
    }, []);

    const parseErrorResponse = useCallback(async (response, fallbackMessage) => {
        let message = fallbackMessage;
        try {
            const payload = await response.json();
            if (typeof payload?.detail === 'string' && payload.detail.trim()) {
                message = payload.detail;
            }
        } catch {
            // Ignore non-JSON error bodies
        }
        return message;
    }, []);

    const fetchTraces = useCallback(async () => {
        if (!enabled) return;
        setLoading(true);
        try {
            const res = await authFetch(`${API_URL}/traces`);
            if (!res.ok) {
                const message = await parseErrorResponse(res, 'Failed to fetch traces');
                setStructuredError(res.status, message);
                return;
            }
            const data = await res.json();
            setTraces(data.traces);
            clearError();
        } catch (e) {
            setStructuredError('NETWORK', e.message || 'Network error while fetching traces');
        } finally {
            setLastFetchAt(new Date().toISOString());
            setLoading(false);
        }
    }, [clearError, enabled, parseErrorResponse, setStructuredError]);

    const fetchTrace = useCallback(async (traceId) => {
        if (!enabled) return null;
        setLoading(true);
        try {
            const res = await authFetch(`${API_URL}/traces/${traceId}`);
            if (!res.ok) {
                const message = await parseErrorResponse(res, 'Failed to fetch trace');
                setStructuredError(res.status, message);
                return null;
            }
            const data = await res.json();
            setSelectedTrace(data);
            clearError();
            return data;
        } catch (e) {
            setStructuredError('NETWORK', e.message || 'Network error while fetching trace');
            return null;
        } finally {
            setLoading(false);
        }
    }, [clearError, enabled, parseErrorResponse, setStructuredError]);

    const fetchTraceTree = useCallback(async (traceId) => {
        if (!enabled) return null;
        try {
            const res = await authFetch(`${API_URL}/traces/${traceId}/tree`);
            if (!res.ok) {
                const message = await parseErrorResponse(res, 'Failed to fetch trace tree');
                setStructuredError(res.status, message);
                return null;
            }
            clearError();
            return await res.json();
        } catch (e) {
            setStructuredError('NETWORK', e.message || 'Network error while fetching trace tree');
            return null;
        }
    }, [clearError, enabled, parseErrorResponse, setStructuredError]);

    const deleteTrace = useCallback(async (traceId) => {
        if (!enabled) return;
        try {
            const response = await authFetch(`${API_URL}/traces/${traceId}`, {
                method: 'DELETE',
            });
            if (!response.ok) {
                const message = await parseErrorResponse(response, 'Failed to delete trace');
                setStructuredError(response.status, message);
                return;
            }
            setTraces(prev => prev.filter(t => t.trace_id !== traceId));
            if (selectedTrace?.trace_id === traceId) {
                setSelectedTrace(null);
            }
            clearError();
        } catch (e) {
            setStructuredError('NETWORK', e.message || 'Network error while deleting trace');
        }
    }, [clearError, enabled, parseErrorResponse, selectedTrace, setStructuredError]);

    const updateTraceInList = useCallback((updatedTrace) => {
        setTraces(prev => prev.map(t =>
            t.trace_id === updatedTrace.trace_id ? updatedTrace : t
        ));
        if (selectedTrace?.trace_id === updatedTrace.trace_id) {
            setSelectedTrace(updatedTrace);
        }
    }, [selectedTrace]);

    const addSpanToTrace = useCallback((span) => {
        setSelectedTrace((prev) => {
            if (prev?.trace_id !== span.trace_id) return prev;

            const existing = prev.spans || [];
            const index = existing.findIndex((item) => item.span_id === span.span_id);
            const spans = [...existing];
            if (index === -1) {
                spans.push(span);
            } else {
                spans[index] = span;
            }
            return {
                ...prev,
                spans,
                ...computeTraceTotals(spans),
            };
        });
    }, []);

    const updateSpanInTrace = useCallback((span) => {
        setSelectedTrace((prev) => {
            if (prev?.trace_id !== span.trace_id) return prev;

            const spans = [...(prev?.spans || [])];
            const index = spans.findIndex((item) => item.span_id === span.span_id);
            if (index === -1) return prev;

            spans[index] = span;
            return {
                ...prev,
                spans,
                ...computeTraceTotals(spans),
            };
        });
    }, []);

    useEffect(() => {
        if (enabled) fetchTraces();
    }, [enabled, fetchTraces]);

    return {
        traces,
        selectedTrace,
        loading,
        error,
        errorCode,
        errorMessage,
        lastFetchAt,
        fetchTraces,
        fetchTrace,
        fetchTraceTree,
        deleteTrace,
        setSelectedTrace,
        updateTraceInList,
        addSpanToTrace,
        updateSpanInTrace,
    };
}
