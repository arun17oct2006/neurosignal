import {
  CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { MarketDataPoint } from "@/types/market";

const axis = { stroke: "var(--muted-foreground)", fontSize: 10, fontFamily: "var(--font-mono)" };
const tip = {
  contentStyle: { background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8, fontFamily: "var(--font-mono)", fontSize: 12 },
  labelStyle: { color: "var(--muted-foreground)" },
};

export function StockChart({ data, loading }: { data: MarketDataPoint[] | undefined; loading: boolean }) {
  if (loading || !data) {
    return (
      <div className="panel p-4">
        <div className="skeleton h-[300px] w-full" />
        <div className="skeleton mt-3 h-[110px] w-full" />
      </div>
    );
  }
  return (
    <div className="panel p-4">
      <div className="mb-2 flex items-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5"><i className="h-0.5 w-4 bg-control" />Close</span>
        <span className="flex items-center gap-1.5"><i className="h-0.5 w-4 bg-neutral" />SMA-20</span>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} syncId="ns" margin={{ left: 0, right: 8 }}>
          <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={axis} hide />
          <YAxis tick={axis} domain={["auto", "auto"]} width={50} />
          <Tooltip {...tip} />
          <Line dataKey="close" stroke="var(--control)" dot={false} strokeWidth={2} />
          <Line dataKey="sma_20" stroke="var(--neutral)" dot={false} strokeWidth={1.5} strokeDasharray="4 3" />
        </LineChart>
      </ResponsiveContainer>
      <p className="mt-2 text-[11px] uppercase tracking-widest text-muted-foreground">RSI (14)</p>
      <ResponsiveContainer width="100%" height={110}>
        <LineChart data={data} syncId="ns" margin={{ left: 0, right: 8 }}>
          <XAxis dataKey="date" tick={axis} minTickGap={40} />
          <YAxis tick={axis} domain={[0, 100]} ticks={[30, 70]} width={50} />
          <ReferenceLine y={70} stroke="var(--sell)" strokeDasharray="3 3" />
          <ReferenceLine y={30} stroke="var(--buy)" strokeDasharray="3 3" />
          <Tooltip {...tip} />
          <Line dataKey="rsi" stroke="var(--foreground)" dot={false} strokeWidth={1.5} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
