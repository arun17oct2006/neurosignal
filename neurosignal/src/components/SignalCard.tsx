import type { AnalysisResponse, SignalType } from "@/types/market";

const style: Record<SignalType, { label: string; cls: string }> = {
  STRONG_BUY: { label: "STRONG BUY", cls: "text-buy border-buy glow-buy bg-buy/10" },
  STRONG_SELL: { label: "STRONG SELL", cls: "text-sell border-sell glow-sell bg-sell/10" },
  NEUTRAL: { label: "NEUTRAL", cls: "text-neutral border-neutral glow-neutral bg-neutral/10" },
};

export function SignalCard({ data, loading }: { data: AnalysisResponse | undefined; loading: boolean }) {
  if (loading || !data) {
    return (
      <div className="panel space-y-4 p-5">
        <div className="skeleton mx-auto h-12 w-48" />
        <div className="skeleton h-24 w-full" />
        {Array.from({ length: 5 }).map((_, i) => <div key={i} className="skeleton h-4 w-full" />)}
      </div>
    );
  }
  const s = style[data.signal];
  const pct = Math.max(-10, Math.min(10, data.predicted_return_pct));
  const angle = (pct / 10) * 90; // -90..90
  const tone = pct >= 0 ? "var(--buy)" : "var(--sell)";

  return (
    <div className="panel p-5">
      <p className="text-[11px] uppercase tracking-widest text-muted-foreground">Model Signal · {data.ticker}</p>
      <div className={`mx-auto mt-3 w-fit rounded-sm border px-5 py-2 font-display text-base font-bold tracking-wider ${s.cls}`}>
        {s.label}
      </div>

      <div className="mt-6">
        <svg viewBox="0 0 200 110" className="mx-auto w-full max-w-[240px]">
          <path d="M10 100 A90 90 0 0 1 190 100" fill="none" stroke="var(--border)" strokeWidth="12" strokeLinecap="round" />
          <path
            d="M100 10 A90 90 0 0 1 190 100"
            fill="none" stroke={pct >= 0 ? tone : "transparent"} strokeWidth="12" strokeLinecap="round"
            strokeDasharray={`${(Math.abs(pct) / 10) * 141} 200`}
          />
          <path
            d="M100 10 A90 90 0 0 0 10 100"
            fill="none" stroke={pct < 0 ? tone : "transparent"} strokeWidth="12" strokeLinecap="round"
            strokeDasharray={`${(Math.abs(pct) / 10) * 141} 200`}
          />
          <line x1="100" y1="100" x2="100" y2="28" stroke="var(--foreground)" strokeWidth="2.5"
            transform={`rotate(${angle} 100 100)`} />
          <circle cx="100" cy="100" r="5" fill="var(--foreground)" />
        </svg>
        <div className="text-center">
          <p className="metric text-2xl font-semibold">${data.target_price.toFixed(2)}</p>
          <p className="metric text-xs" style={{ color: tone }}>
            {pct >= 0 ? "+" : ""}{data.predicted_return_pct.toFixed(2)}% target
          </p>
        </div>
      </div>

      {data.feature_importance && (
        <div className="mt-6 space-y-2.5">
          <p className="text-[11px] uppercase tracking-widest text-muted-foreground">Feature Importance</p>
          {data.feature_importance.map((f) => (
            <div key={f.feature}>
              <div className="flex justify-between text-xs">
                <span>{f.feature}</span>
                <span className="metric text-muted-foreground">{(f.weight * 100).toFixed(0)}%</span>
              </div>
              <div className="mt-1 h-1.5 rounded-full bg-muted">
                <div className="h-full rounded-full bg-control" style={{ width: `${f.weight * 100 / 0.35}%` }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
