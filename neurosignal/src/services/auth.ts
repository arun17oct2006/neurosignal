import type { UserSession } from "@/types/market";
import { API_BASE, ApiError } from "./api";

const KEY = "neurosignal.session";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}/auth${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).catch(() => {
    throw new ApiError(`Cannot reach backend at ${API_BASE}`);
  });
  if (!res.ok) {
    const b = (await res.json().catch(() => null)) as { detail?: string } | null;
    throw new ApiError(b?.detail ?? `Auth failed (${res.status})`, res.status);
  }
  return res.json() as Promise<T>;
}

function persist(s: UserSession) {
  localStorage.setItem(KEY, JSON.stringify(s));
  return s;
}

export function getSession(): UserSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as UserSession) : null;
  } catch {
    return null;
  }
}

export async function requestMagicLink(email: string): Promise<void> {
  await post("/magic-link", { email, redirect: window.location.origin });
}

export async function requestOtp(email: string): Promise<void> {
  await post("/otp/request", { email });
}

export async function verifyOtp(email: string, code: string): Promise<UserSession> {
  if (!/^\d{6}$/.test(code)) throw new ApiError("Enter the 6-digit code");
  return persist(await post<UserSession>("/otp/verify", { email, code }));
}

export const isPasskeySupported = () =>
  typeof window !== "undefined" && "PublicKeyCredential" in window;

export async function signInWithPasskey(email: string): Promise<UserSession> {
  if (!isPasskeySupported()) throw new ApiError("Passkeys not supported on this device");
  const options = await post<PublicKeyCredentialRequestOptions>("/webauthn/options", { email });
  const cred = await navigator.credentials.get({ publicKey: options });
  return persist(await post<UserSession>("/webauthn/verify", { email, credential: cred }));
}

export async function signOut(): Promise<void> {
  localStorage.removeItem(KEY);
  await post("/logout", {}).catch(() => undefined);
}
