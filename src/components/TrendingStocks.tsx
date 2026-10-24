const TRENDING = [
  { symbol: "NVDA", name: "NVIDIA" },
  { symbol: "AAPL", name: "Apple" },
  { symbol: "MSFT", name: "Microsoft" },
  { symbol: "TSLA", name: "Tesla" },
  { symbol: "GOOGL", name: "Google" },
  { symbol: "AMZN", name: "Amazon" },
];

export const TRENDING_SYMBOLS = TRENDING.map((s) => s.symbol);

export function TrendingStocks({ onPick }: { onPick: (symbol: string) => void }) {
  return (
    <section className="rounded-xl border border-white/10 bg-neutral-900 p-6 text-neutral-100">
      <h2 className="text-lg font-semibold">Top stocks</h2>
      <p className="mt-1 text-xs opacity-60">
        Pick a stock to see its live price, model signals and analysis. Or search any symbol above.
      </p>
      <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
        {TRENDING.map((s) => (
          <button
            key={s.symbol}
            type="button"
            onClick={() => onPick(s.symbol)}
            className="rounded-lg bg-neutral-800 p-4 text-left transition hover:bg-neutral-700"
          >
            <p className="text-sm font-semibold">{s.name}</p>
            <p className="mt-1 text-[11px] opacity-60">{s.symbol}</p>
          </button>
        ))}
      </div>
    </section>
  );
}