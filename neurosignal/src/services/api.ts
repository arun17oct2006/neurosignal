import type { AnalysisResponse, ChatSummaryContext } from "@/types/market";

/**
 * All network I/O for NeuroSignal AI goes through this module.
 * Talks to the FastAPI backend in /backend. Override with VITE_NEUROSIGNAL_API_URL.
 */
export const API_BASE =
  (import.meta.env["VITE_NEUROSIGNAL_API_URL"] as string | undefined) ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(`Cannot reach backend at ${API_BASE}`);
  }
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: string } | null;
    throw new ApiError(body?.detail ?? `Request failed (${res.status})`, res.status);
  }
  return res.json() as Promise<T>;
}

export async function fetchAnalysis(ticker: string): Promise<AnalysisResponse> {
  const t = ticker.trim().toUpperCase();
  if (!t) throw new ApiError("Ticker required");
  return request<AnalysisResponse>(`/analysis/${encodeURIComponent(t)}`);
}

export async function analyzeDataset(
  label: string,
  rows: { date: string; close: number }[],
): Promise<AnalysisResponse> {
  return request<AnalysisResponse>(`/analysis/dataset`, {
    method: "POST",
    body: JSON.stringify({ label, rows }),
  });
}

/** Streams the assistant reply via SSE. Only summary metrics are sent. */
export async function streamChat(
  question: string,
  ctx: ChatSummaryContext,
  onToken: (t: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ q: question, ctx }),
    signal: signal ?? null,
  }).catch(() => {
    throw new ApiError(`Cannot reach backend at ${API_BASE}`);
  });
  if (!res.ok || !res.body) throw new ApiError(`Chat failed (${res.status})`, res.status);
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() ?? "";
    for (const p of parts) {
      const data = p.replace(/^data: ?/gm, "");
      if (data === "[DONE]") return;
      onToken(JSON.parse(data) as string);
    }
  }
}
