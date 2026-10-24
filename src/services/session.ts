/**
 * Session storage for the Google-authenticated user.
 * Stores only what the backend returns: profile fields + our signed JWT.
 * No passwords, no Google credentials are kept.
 */

export interface StoredSession {
  user_id: string;          // Google's stable "sub" id
  email: string;
  name: string;
  picture: string;
  authenticated_via: "google";
  token: string;            // our backend-issued JWT
}

const KEY = "neurosignal.session";

export function getSession(): StoredSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as StoredSession) : null;
  } catch {
    return null;
  }
}

export function saveSession(session: StoredSession): void {
  window.localStorage.setItem(KEY, JSON.stringify(session));
}

export function clearSession(): void {
  window.localStorage.removeItem(KEY);
}

/** Headers to attach to backend calls. Empty object when logged out. */
export function getAuthHeaders(): Record<string, string> {
  const s = getSession();
  return s ? { Authorization: `Bearer ${s.token}` } : {};
}
