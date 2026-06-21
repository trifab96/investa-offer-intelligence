import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Legend,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";
import { compareOffers, listOffers } from "../api";
import ScoreBadge from "../components/ScoreBadge";

const COLORS = ["#0E3B4C", "#2A7088", "#C8A15A", "#4C8FA6"];

export default function ComparePage() {
  const { data: offers } = useQuery({ queryKey: ["offers"], queryFn: listOffers });
  const [selected, setSelected] = useState<string[]>([]);

  const { data: comparison } = useQuery({
    queryKey: ["compare", selected],
    queryFn: () => compareOffers(selected),
    enabled: selected.length >= 2,
  });

  const scored = (offers ?? []).filter((o) => o.score != null);

  function toggle(id: string) {
    setSelected((prev) =>
      prev.includes(id)
        ? prev.filter((x) => x !== id)
        : prev.length < 4
          ? [...prev, id]
          : prev,
    );
  }

  const radarData = buildRadarData(comparison ?? []);

  return (
    <div className="space-y-8">
      <div>
        <p className="eyebrow">Portfolio</p>
        <h1 className="mt-1 font-display text-3xl text-investa-900">
          Angebote vergleichen
        </h1>
        <p className="mt-2 text-sm text-slate-500">
          Wählen Sie 2–4 bewertete Angebote für den direkten Vergleich.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {scored.map((o) => (
          <label
            key={o.id}
            className={`flex cursor-pointer items-center gap-3 rounded-lg border p-4 transition ${
              selected.includes(o.id)
                ? "border-investa-500 bg-investa-500/5"
                : "border-slate-200 bg-white hover:border-investa-300"
            }`}
          >
            <input
              type="checkbox"
              className="accent-investa-600"
              checked={selected.includes(o.id)}
              onChange={() => toggle(o.id)}
            />
            <span className="flex-1 text-sm text-slate-700">
              {o.subject || "(ohne Betreff)"}
            </span>
            <ScoreBadge score={o.score} band={o.band} />
          </label>
        ))}
        {scored.length === 0 && (
          <p className="text-sm text-slate-400">Noch keine bewerteten Angebote.</p>
        )}
      </div>

      {comparison && comparison.length >= 2 && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="card card-pad">
            <h2 className="card-title mb-4">Sub-Scores</h2>
            <ResponsiveContainer width="100%" height={320}>
              <RadarChart data={radarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="metric" />
                {comparison.map((c, i) => (
                  <Radar
                    key={c.id}
                    name={c.subject || c.id.slice(0, 6)}
                    dataKey={c.id}
                    stroke={COLORS[i % COLORS.length]}
                    fill={COLORS[i % COLORS.length]}
                    fillOpacity={0.25}
                  />
                ))}
                <Legend />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          <div className="card card-pad overflow-auto">
            <h2 className="card-title mb-4">Kennzahlen</h2>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-widest2 text-slate-500">
                  <th className="py-2">Angebot</th>
                  <th className="py-2">Score</th>
                  <th className="py-2">Rendite %</th>
                  <th className="py-2">€/m²</th>
                </tr>
              </thead>
              <tbody>
                {comparison.map((c) => (
                  <tr key={c.id} className="border-t border-slate-100">
                    <td className="py-2 text-slate-700">{c.subject || c.id.slice(0, 6)}</td>
                    <td className="py-2 font-medium tabular-nums">{c.score?.toFixed(1) ?? "—"}</td>
                    <td className="py-2 tabular-nums">{c.metrics?.gross_yield_pct ?? "—"}</td>
                    <td className="py-2 tabular-nums">{c.metrics?.price_per_m2 ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function buildRadarData(comparison: any[]): any[] {
  const metricNames = new Set<string>();
  comparison.forEach((c) =>
    (c.subscores ?? []).forEach((s: any) => metricNames.add(s.name)),
  );
  return Array.from(metricNames).map((metric) => {
    const row: Record<string, any> = { metric };
    comparison.forEach((c) => {
      const sub = (c.subscores ?? []).find((s: any) => s.name === metric);
      row[c.id] = sub ? sub.value : 0;
    });
    return row;
  });
}
