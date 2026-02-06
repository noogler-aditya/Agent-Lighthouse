import { useState, useEffect, useCallback } from 'react';

const API_URL = 'http://localhost:8000/api';

export function useTraces() {
    const [traces, setTraces] = useState([]);
    const [selectedTrace, setSelectedTrace] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const fetchTraces = useCallback(async () => {
        setLoading(true);
        try {
            const res = await fetch(`${API_URL}/traces`);
            if (!res.ok) throw new Error('Failed to fetch traces');
            const data = await res.json();
            setTraces(data.traces);
            setError(null);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchTrace = useCallback(async (traceId) => {
        setLoading(true);
        try {
            const res = await fetch(`${API_URL}/traces/${traceId}`);
            if (!res.ok) throw new Error('Failed to fetch trace');
            const data = await res.json();
            setSelectedTrace(data);
            setError(null);
            return data;
        } catch (e) {
            setError(e.message);
            return null;
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchTraceTree = useCallback(async (traceId) => {
        try {
            const res = await fetch(`${API_URL}/traces/${traceId}/tree`);
            if (!res.ok) throw new Error('Failed to fetch trace tree');
            return await res.json();
        } catch (e) {
            setError(e.message);
            return null;
        }
    }, []);

    const deleteTrace = useCallback(async (traceId) => {
        try {
            await fetch(`${API_URL}/traces/${traceId}`, { method: 'DELETE' });
            setTraces(prev => prev.filter(t => t.trace_id !== traceId));
            if (selectedTrace?.trace_id === traceId) {
                setSelectedTrace(null);
            }
        } catch (e) {
            setError(e.message);
        }
    }, [selectedTrace]);

    const updateTraceInList = useCallback((updatedTrace) => {
        setTraces(prev => prev.map(t =>
            t.trace_id === updatedTrace.trace_id ? updatedTrace : t
        ));
        if (selectedTrace?.trace_id === updatedTrace.trace_id) {
            setSelectedTrace(updatedTrace);
        }
    }, [selectedTrace]);

    const addSpanToTrace = useCallback((span) => {
        if (selectedTrace?.trace_id === span.trace_id) {
            setSelectedTrace(prev => ({
                ...prev,
                spans: [...prev.spans, span]
            }));
        }
    }, [selectedTrace]);

    useEffect(() => {
        fetchTraces();
    }, [fetchTraces]);

    return {
        traces,
        selectedTrace,
        loading,
        error,
        fetchTraces,
        fetchTrace,
        fetchTraceTree,
        deleteTrace,
        setSelectedTrace,
        updateTraceInList,
        addSpanToTrace,
    };
}
