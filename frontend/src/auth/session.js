import { API_BASE_URL } from '../config';

const REFRESH_TOKEN_KEY = 'lighthouse_refresh_token';
const ACCESS_TOKEN_KEY = 'lighthouse_access_token';
const USER_SUBJECT_KEY = 'lighthouse_user_subject';

let accessToken = localStorage.getItem(ACCESS_TOKEN_KEY) || '';
let subject = localStorage.getItem(USER_SUBJECT_KEY) || '';
let refreshPromise = null;

localStorage.removeItem('lighthouse_user_role');

function parseJwt(token) {
  try {
    const payload = token.split('.')[1];
    if (!payload) return null;
    return JSON.parse(atob(payload));
  } catch {
    return null;
  }
}

function tokenExpired(token) {
  if (!token) return true;
  const payload = parseJwt(token);
  if (!payload?.exp) return true;
  return Date.now() >= payload.exp * 1000 - 5000;
}

function persistAccessToken(token) {
  accessToken = token || '';
  if (accessToken) {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    const payload = parseJwt(accessToken) || {};
    subject = payload.sub || '';
    if (subject) localStorage.setItem(USER_SUBJECT_KEY, subject);
  } else {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(USER_SUBJECT_KEY);
    subject = '';
  }
}

function setRefreshToken(token) {
  if (token) localStorage.setItem(REFRESH_TOKEN_KEY, token);
  else localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function getAccessToken() {
  return accessToken;
}

export function getAuthContext() {
  return {
    subject,
    isAuthenticated: Boolean(accessToken),
  };
}

export async function loginWithPassword(username, password) {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || 'Login failed');
  }

  const data = await response.json();
  persistAccessToken(data.access_token);
  setRefreshToken(data.refresh_token);
  return getAuthContext();
}

export async function registerWithPassword(username, password) {
  const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || 'Registration failed');
  }

  const data = await response.json();
  persistAccessToken(data.access_token);
  setRefreshToken(data.refresh_token);
  return { ...getAuthContext(), apiKey: data.api_key };
}

export function clearSession() {
  persistAccessToken('');
  setRefreshToken('');
}

export async function refreshSession() {
  if (refreshPromise) return refreshPromise;

  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refreshToken) {
    clearSession();
    throw new Error('No refresh token');
  }

  refreshPromise = (async () => {
    const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      clearSession();
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || 'Session refresh failed');
    }

    const data = await response.json();
    persistAccessToken(data.access_token);
    setRefreshToken(data.refresh_token);
    return getAuthContext();
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

export async function bootstrapSession() {
  if (!tokenExpired(accessToken)) return getAuthContext();
  return refreshSession();
}

export async function authFetch(input, init = {}) {
  let token = getAccessToken();
  if (tokenExpired(token)) {
    try {
      await refreshSession();
      token = getAccessToken();
    } catch {
      // allow first request to fail with 401 if no active session
    }
  }

  const headers = new Headers(init.headers || {});
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const first = await fetch(input, { ...init, headers });
  if (first.status !== 401) return first;

  try {
    await refreshSession();
  } catch {
    return first;
  }

  const retryHeaders = new Headers(init.headers || {});
  const refreshed = getAccessToken();
  if (refreshed) retryHeaders.set('Authorization', `Bearer ${refreshed}`);
  return fetch(input, { ...init, headers: retryHeaders });
}
