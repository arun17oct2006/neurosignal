import { Fragment } from "react";

type ModelCard = {
  label: string;
  direction: "UP" | "DOWN" | "HOLD";
  predicted_change_pct: number | null;
  predicted_price: number | null;
};

type ModelData = {
  models?: Record<string, ModelCard>;
  consensus?: string;
  currency_symbol?: string;
};

const STYLE: Record<string, string> = {
  UP: "text-emerald-400",
  DOWN: "text-red-400",
  HOLD: "text-neutral-400",
  MIXED: "text-yellow-400",
};

export function ModelPanel({ data }: { data?: ModelData }) {
  const models = data?.models;
  if (!models) return null;

  const entries = Object.entries(models);
  const consensus = data?.consensus ?? "MIXED";
  const cur = data?.currency_symbol ?? "₹";

  return (
    <section className="rounded-xl border border-white/10 bg-neutral-900 p-4 text-neutral-100">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Model ensemble ({entries.length} models)</h3>
        <span className={`text-xs font-semibold ${STYLE[consensus] ?? ""}`}>Consensus: {consensus}</span>
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {entries.map(([key, m]) => (
          <div key={key} className="rounded-lg bg-neutral-800 p-3">
            <p className="text-xs opacity-70">{m.label}</p>
            <p className={`mt-1 text-lg font-semibold ${STYLE[m.direction] ?? ""}`}>{m.direction}</p>
            <p className="text-xs opacity-70">
              {m.predicted_price != null ? `${cur}${Number(m.predicted_price).toFixed(2)}` : "no price"}
              {m.predicted_change_pct != null && (
                <Fragment>
                  {" "}({m.predicted_change_pct >= 0 ? "+" : ""}{m.predicted_change_pct}%)
                </Fragment>
              )}
            </p>
          </div>
        ))}
      </div>

      <p className="mt-3 text-[11px] opacity-50">Model outputs are research signals, not investment advice.</p>
    </section>
  );
}