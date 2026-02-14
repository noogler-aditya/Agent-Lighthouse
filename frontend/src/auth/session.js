import { API_BASE_URL, SUPABASE_ANON_KEY, SUPABASE_URL } from '../config';

const REFRESH_TOKEN_KEY = 'lighthouse_refresh_token';
const USER_ROLE_KEY = 'lighthouse_user_role';
const USER_SUBJECT_KEY = 'lighthouse_user_subject';

let accessToken = '';
let refreshToken = sessionStorage.getItem(REFRESH_TOKEN_KEY) || '';
let subject = sessionStorage.getItem(USER_SUBJECT_KEY) || '';
let role = sessionStorage.getItem(USER_ROLE_KEY) || '';
let refreshPromise = null;

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

function persistSession(token, nextRefreshToken) {
  accessToken = token || '';
  refreshToken = nextRefreshToken || '';

  if (refreshToken) sessionStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  else sessionStorage.removeItem(REFRESH_TOKEN_KEY);

  if (accessToken) {
    const payload = parseJwt(accessToken) || {};
    subject = payload.sub || '';
    const rawRole = payload?.app_metadata?.role || payload?.role || 'viewer';
    role = String(rawRole || 'viewer');
    if (subject) sessionStorage.setItem(USER_SUBJECT_KEY, subject);
    if (role) sessionStorage.setItem(USER_ROLE_KEY, role);
  } else {
    sessionStorage.removeItem(USER_SUBJECT_KEY);
    sessionStorage.removeItem(USER_ROLE_KEY);
    subject = '';
    role = '';
  }
}

function ensureSupabaseConfig() {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    throw new Error('Supabase auth is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.');
  }
}

async function supabaseAuthRequest(grantType, payload) {
  ensureSupabaseConfig();
  const response = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=${grantType}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      apikey: SUPABASE_ANON_KEY,
    },
    body: JSON.stringify(payload),
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.error_description || body.msg || body.error || 'Authentication failed');
  }
  return body;
}

export function getAccessToken() {
  return accessToken;
}

export function getAuthContext() {
  return {
    subject,
    role,
    isAuthenticated: Boolean(accessToken),
  };
}

export async function loginWithPassword(email, password) {
  const data = await supabaseAuthRequest('password', { email, password });
  persistSession(data.access_token, data.refresh_token);
  return getAuthContext();
}

export function clearSession() {
  accessToken = '';
  persistSession('', '');
}

export async function refreshSession() {
  if (refreshPromise) return refreshPromise;
  if (!refreshToken) {
    clearSession();
    throw new Error('No refresh token');
  }

  refreshPromise = (async () => {
    const data = await supabaseAuthRequest('refresh_token', { refresh_token: refreshToken });
    persistSession(data.access_token, data.refresh_token || refreshToken);
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

export function getApiBaseUrl() {
  return API_BASE_URL;
}
