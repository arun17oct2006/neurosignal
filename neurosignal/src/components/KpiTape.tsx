import type { AnalysisResponse } from "@/types/market";

export function KpiTape({ data, loading }: { data: AnalysisResponse | undefined; loading: boolean }) {
  const items = data
    ? [
        { label: "Live Price", value: `$${data.live_price.toFixed(2)}` },
        {
          label: "Target / Return",
          value: `$${data.target_price.toFixed(2)}`,
          sub: `${data.predicted_return_pct >= 0 ? "+" : ""}${data.predicted_return_pct.toFixed(2)}%`,
          tone: data.predicted_return_pct >= 0 ? "text-buy" : "text-sell",
        },
        { label: "Hit Ratio", value: `${data.hit_ratio.toFixed(1)}%` },
        {
          label: "RSI (14)",
          value: data.rsi_now.toFixed(1),
          tone: data.rsi_now > 70 ? "text-sell" : data.rsi_now < 30 ? "text-buy" : "text-neutral",
        },
        { label: "ML Model", value: data.model_used, sub: `RMSE ${data.rmse.toFixed(3)}` },
      ]
    : [];

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
      {loading || !data
        ? Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="panel p-4">
              <div className="skeleton h-3 w-20" />
              <div className="skeleton mt-3 h-6 w-28" />
            </div>
          ))
        : items.map((k) => (
            <div key={k.label} className="panel p-4">
              <p className="text-[11px] uppercase tracking-widest text-muted-foreground">{k.label}</p>
              <p className={`metric mt-1 text-xl font-semibold ${k.sub ? "" : (k.tone ?? "")}`}>{k.value}</p>
              {k.sub && <p className={`metric text-xs ${k.tone ?? "text-muted-foreground"}`}>{k.sub}</p>}
            </div>
          ))}
    </div>
  );
}
