export function bandColor(band: string | null | undefined): string {
  switch (band) {
    case "pursue":
      return "bg-emerald-50 text-emerald-700 border-emerald-200";
    case "review":
      return "bg-amber-50 text-amber-700 border-amber-200";
    case "reject":
      return "bg-rose-50 text-rose-700 border-rose-200";
    default:
      return "bg-slate-50 text-slate-500 border-slate-200";
  }
}

export function bandLabel(band: string | null | undefined): string {
  switch (band) {
    case "pursue":
      return "Verfolgen";
    case "review":
      return "Prüfen";
    case "reject":
      return "Ablehnen";
    default:
      return "—";
  }
}

export default function ScoreBadge({
  score,
  band,
}: {
  score: number | null | undefined;
  band: string | null | undefined;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-sm font-semibold tabular-nums ${bandColor(
        band,
      )}`}
    >
      {score != null ? score.toFixed(1) : "—"}
      <span className="text-xs font-normal opacity-70">/ 10</span>
    </span>
  );
}
