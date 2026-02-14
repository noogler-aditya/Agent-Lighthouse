const rawApiUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');
const wsOverride = import.meta.env.VITE_WS_URL || '';

function toWebSocketUrl(httpUrl) {
  try {
    const url = new URL(httpUrl, window.location.origin);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    url.pathname = '/ws';
    url.search = '';
    return url.toString();
  } catch {
    return 'ws://localhost:8000/ws';
  }
}

export const API_BASE_URL = rawApiUrl;
export const API_URL = rawApiUrl.endsWith('/api') ? rawApiUrl : `${rawApiUrl}/api`;
export const WS_URL = wsOverride || toWebSocketUrl(rawApiUrl);
