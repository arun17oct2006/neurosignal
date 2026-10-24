import { API_BASE, ApiError } from "./api";
import { type StoredSession, clearSession, saveSession, getSession } from "./session";

export { getSession };

interface BackendAuthResponse {
  access_token: string;
  profile: {
    sub: string;
    email: string;
    name: string;
    picture: string;
    email_verified: boolean;
  };
}

/** Sends the Google ID token to FastAPI, stores the returned session. */
export async function loginWithGoogle(credential: string): Promise<StoredSession> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/auth/google`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ credential }),
    });
  } catch {
    throw new ApiError(`Cannot reach backend at ${API_BASE}`);
  }

  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: string } | null;
    throw new ApiError(body?.detail ?? `Sign-in failed (${res.status})`, res.status);
  }

  const data = (await res.json()) as BackendAuthResponse;
  const session: StoredSession = {
    user_id: data.profile.sub,
    email: data.profile.email,
    name: data.profile.name,
    picture: data.profile.picture,
    authenticated_via: "google",
    token: data.access_token,
  };
  saveSession(session);
  return session;
}

export async function signOut(): Promise<void> {
  clearSession();
  // Tell Google not to auto-select the account on the next visit
  window.google?.accounts.id.disableAutoSelect();
  await fetch(`${API_BASE}/auth/logout`, { method: "POST" }).catch(() => undefined);
}
