const API_URL = import.meta.env.VITE_NEUROSIGNAL_API_URL ?? "http://localhost:8000";

export type TrendingItem = {
  symbol: string;
  name: string;
  price: number | null;
  change_pct: number | null;
  volume_ratio: number | null;
  currency: string;
  reasons: string[];
};

export async function fetchTrendingWorldwide(): Promise<TrendingItem[]> {
  const res = await fetch(`${API_URL}/trending/worldwide`);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? `Request failed (${res.status})`);
  return data.items as TrendingItem[];
}