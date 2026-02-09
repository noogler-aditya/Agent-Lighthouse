import { useState, useCallback } from 'react';
import { API_URL } from '../config';
import { authFetch } from '../auth/session';

export function useAgentState(traceId, enabled = true) {
    const [state, setState] = useState(null);
    const [controlStatus, setControlStatus] = useState('unknown');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const fetchState = useCallback(async () => {
        if (!enabled || !traceId) return;
        setLoading(true);
        try {
            const res = await authFetch(`${API_URL}/state/${traceId}`);
            if (res.ok) {
                const data = await res.json();
                setState(data);
                setControlStatus(data.control?.status || 'unknown');
            } else if (res.status === 404) {
                setState(null);
                setControlStatus('unknown');
            } else {
                throw new Error('Failed to fetch state');
            }
            setError(null);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, [enabled, traceId]);

    const modifyState = useCallback(async (path, value) => {
        if (!enabled || !traceId) return;
        try {
            const res = await authFetch(`${API_URL}/state/${traceId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path, value }),
            });
            if (!res.ok) throw new Error('Failed to modify state');
            await fetchState();
        } catch (e) {
            setError(e.message);
        }
    }, [enabled, traceId, fetchState]);

    const bulkModifyState = useCallback(async (updates) => {
        if (!enabled || !traceId) return;
        try {
            const res = await authFetch(`${API_URL}/state/${traceId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updates),
            });
            if (!res.ok) throw new Error('Failed to update state');
            await fetchState();
        } catch (e) {
            setError(e.message);
        }
    }, [enabled, traceId, fetchState]);

    const pause = useCallback(async () => {
        if (!enabled || !traceId) return;
        try {
            const response = await authFetch(`${API_URL}/state/${traceId}/pause`, {
                method: 'POST',
            });
            if (!response.ok) throw new Error('Failed to pause execution');
            setControlStatus('paused');
        } catch (e) {
            setError(e.message);
        }
    }, [enabled, traceId]);

    const resume = useCallback(async () => {
        if (!enabled || !traceId) return;
        try {
            const response = await authFetch(`${API_URL}/state/${traceId}/resume`, {
                method: 'POST',
            });
            if (!response.ok) throw new Error('Failed to resume execution');
            setControlStatus('running');
        } catch (e) {
            setError(e.message);
        }
    }, [enabled, traceId]);

    const step = useCallback(async (count = 1) => {
        if (!enabled || !traceId) return;
        try {
            const response = await authFetch(`${API_URL}/state/${traceId}/step`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ count }),
            });
            if (!response.ok) throw new Error('Failed to step execution');
            setControlStatus('step');
        } catch (e) {
            setError(e.message);
        }
    }, [enabled, traceId]);

    return {
        state,
        controlStatus,
        loading,
        error,
        fetchState,
        modifyState,
        bulkModifyState,
        pause,
        resume,
        step,
        setControlStatus,
    };
}
