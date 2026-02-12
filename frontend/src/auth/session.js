import { supabase } from './supabaseClient';

let currentSession = null;
let currentUser = null;

supabase.auth.onAuthStateChange((_event, session) => {
  currentSession = session;
  currentUser = session?.user ?? null;
});

async function getSession() {
  if (currentSession) return currentSession;
  const { data, error } = await supabase.auth.getSession();
  if (error) throw error;
  currentSession = data.session;
  currentUser = data.session?.user ?? null;
  return currentSession;
}

export function getAuthContext() {
  return {
    subject: currentUser?.email || currentUser?.id || '',
    isAuthenticated: Boolean(currentSession?.access_token),
  };
}

export async function loginWithPassword(email, password) {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) throw error;
  currentSession = data.session;
  currentUser = data.user;
  return getAuthContext();
}

export async function registerWithPassword(email, password) {
  const { data, error } = await supabase.auth.signUp({ email, password });
  if (error) throw error;
  currentSession = data.session;
  currentUser = data.user;
  return { ...getAuthContext(), apiKey: null };
}

export async function clearSession() {
  await supabase.auth.signOut();
  currentSession = null;
  currentUser = null;
}

export async function bootstrapSession() {
  await getSession();
  return getAuthContext();
}

export async function authFetch(input, init = {}) {
  const session = await getSession();
  const headers = new Headers(init.headers || {});
  if (session?.access_token) headers.set('Authorization', `Bearer ${session.access_token}`);
  return fetch(input, { ...init, headers });
}

export async function getAccessToken() {
  const session = await getSession();
  return session?.access_token || '';
}

export async function refreshSession() {
  const { data, error } = await supabase.auth.refreshSession();
  if (error) throw error;
  currentSession = data.session;
  currentUser = data.user;
  return getAuthContext();
}
