import { useRef, useState } from "react";
import Papa from "papaparse";

interface Props {
  onParsed: (label: string, rows: { date: string; close: number }[]) => void;
}

export function DatasetUploader({ onParsed }: Props) {
  const [drag, setDrag] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);

  const handle = (file: File) => {
    setError(null);
    Papa.parse<Record<string, string>>(file, {
      header: true,
      skipEmptyLines: true,
      complete: (res) => {
        const fields = (res.meta.fields ?? []).map((f) => f.toLowerCase());
        const dKey = res.meta.fields?.[fields.findIndex((f) => f.includes("date"))];
        const cKey = res.meta.fields?.[fields.findIndex((f) => f.includes("close"))];
        if (!dKey || !cKey) return setError("CSV needs 'date' and 'close' columns");
        const rows = res.data
          .map((r) => ({ date: r[dKey] ?? "", close: parseFloat(r[cKey] ?? "") }))
          .filter((r) => r.date && Number.isFinite(r.close));
        onParsed(file.name.replace(/\.csv$/i, ""), rows);
      },
      error: (e) => setError(e.message),
    });
  };

  return (
    <div>
      <button
        type="button"
        onClick={() => input.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          const f = e.dataTransfer.files[0];
          if (f) handle(f);
        }}
        className={`w-full rounded-lg border border-dashed px-4 py-3 text-left text-xs transition ${
          drag ? "border-control bg-control/10 text-control" : "text-muted-foreground hover:border-control/60"
        }`}
      >
        <span className="font-semibold text-foreground">Drop CSV</span> or click — columns: date, close
      </button>
      <input
        ref={input}
        type="file"
        accept=".csv,text/csv"
        hidden
        onChange={(e) => e.target.files?.[0] && handle(e.target.files[0])}
      />
      {error && <p className="mt-2 text-xs text-sell">{error}</p>}
    </div>
  );
}
