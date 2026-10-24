import { useEffect, useState } from "react";
import { fetchTrendingWorldwide, type TrendingItem } from "@/services/trending";

const SYMBOL_SIGN: Record<string, string> = { USD: "$", INR: "₹" };

export function TrendingWorldwide({ onPick }: { onPick: (symbol: string) => void }) {
  const [items, setItems] = useState<TrendingItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTrendingWorldwide()
      .then(setItems)
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <section className="rounded-xl border border-white/10 bg-neutral-900 p-6 text-neutral-100">
      <h2 className="text-lg font-semibold">Trending worldwide</h2>
      <p className="mt-1 text-xs opacity-60">
        Ranked by unusual trading volume and price move. Updated every 15 minutes.
      </p>

      {error && <p className="mt-4 text-xs text-red-400">Could not load trending stocks: {error}</p>}
      {!items && !error && <p className="mt-4 text-xs opacity-60">Loading trending stocks...</p>}

      {items && (
        <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
          {items.map((s) => {
            const up = (s.change_pct ?? 0) >= 0;
            const sign = SYMBOL_SIGN[s.currency] ?? s.currency + " ";
            return (
              <button
                key={s.symbol}
                type="button"
                onClick={() => onPick(s.symbol)}
                className="rounded-lg bg-neutral-800 p-4 text-left transition hover:bg-neutral-700"
              >
                <p className="truncate text-sm font-semibold">{s.name}</p>
                <p className="mt-1 text-[11px] opacity-60">{s.symbol}</p>
                {s.price != null && <p className="mt-2 text-sm">{sign}{s.price.toFixed(2)}</p>}
                {s.change_pct != null && (
                  <p className={`text-xs ${up ? "text-emerald-400" : "text-red-400"}`}>
                    {up ? "+" : ""}{s.change_pct}%
                  </p>
                )}
                {s.volume_ratio != null && (
                  <p className="mt-1 text-[10px] opacity-50">{s.volume_ratio}x avg volume</p>
                )}
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}