import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
} from "recharts";
import { getStats } from "../api";
import type { OfferSummary, PortfolioStats } from "../types";

function bucketColor(idx: number): string {
  if (idx >= 7) return "#0E3B4C";
  if (idx >= 4) return "#C8A15A";
  return "#9F4456";
}

/** Portfolio-level decision-support overview shown above the offer list. */
export default function DashboardStats() {
  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: getStats,
    refetchInterval: (q) => {
      const s = q.state.data as PortfolioStats | undefined;
      return s && s.processing > 0 ? 2500 : false;
    },
  });

  if (!stats || stats.total === 0) return null;

  const hist = stats.score_histogram.map((count, i) => ({
    bucket: `${i}`,
    count,
    idx: i,
  }));

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
      <Kpi label="Angebote gesamt" value={stats.total} sub={`${stats.done} analysiert`} />
      <Kpi
        label="Ø Score"
        value={stats.avg_score != null ? stats.avg_score.toFixed(1) : "—"}
        sub={`${stats.scored} bewertet`}
        accent
      />
      <Kpi
        label="Verfolgen / Prüfen / Ablehnen"
        value={`${stats.band_counts.pursue ?? 0} / ${stats.band_counts.review ?? 0} / ${
          stats.band_counts.reject ?? 0
        }`}
        sub="Empfehlungen"
      />
      <Kpi
        label="Dubletten erkannt"
        value={stats.known_duplicates}
        sub={stats.processing > 0 ? `${stats.processing} in Bearbeitung` : "bereits bekannt"}
      />

      <div className="card card-pad lg:col-span-2">
        <h3 className="card-title mb-3">Score-Verteilung</h3>
        <ResponsiveContainer width="100%" height={140}>
          <BarChart data={hist}>
            <XAxis dataKey="bucket" tickLine={false} axisLine={false} fontSize={11} />
            <Tooltip
              cursor={{ fill: "#f1f5f9" }}
              formatter={(v: any) => [`${v} Angebote`, "Anzahl"]}
              labelFormatter={(l) => `Score ${l}–${Number(l) + 1}`}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {hist.map((h) => (
                <Cell key={h.idx} fill={bucketColor(h.idx)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="card card-pad lg:col-span-2">
        <h3 className="card-title mb-3">Top-Angebote</h3>
        {stats.top_offers.length === 0 && (
          <p className="text-sm text-slate-400">Noch keine bewerteten Angebote.</p>
        )}
        <ul className="space-y-2">
          {stats.top_offers.map((o: OfferSummary) => (
            <li key={o.id} className="flex items-center justify-between gap-3 text-sm">
              <span className="truncate text-slate-600">{o.subject || "(ohne Betreff)"}</span>
              <span className="shrink-0 font-semibold tabular-nums text-investa-700">
                {o.score?.toFixed(1)}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function Kpi({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <div className={`card card-pad ${accent ? "bg-investa-800 text-white" : ""}`}>
      <p
        className={`text-[11px] font-semibold uppercase tracking-widest2 ${
          accent ? "text-investa-300" : "text-investa-500"
        }`}
      >
        {label}
      </p>
      <p className="mt-2 font-display text-3xl">{value}</p>
      {sub && (
        <p className={`mt-1 text-xs ${accent ? "text-investa-300" : "text-slate-400"}`}>
          {sub}
        </p>
      )}
    </div>
  );
}
