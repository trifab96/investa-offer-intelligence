import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { listOffers } from "../api";
import type { OfferSummary } from "../types";
import ScoreBadge, { bandLabel } from "../components/ScoreBadge";
import UploadBox from "../components/UploadBox";
import DashboardStats from "../components/DashboardStats";

const ACTIVE = ["received", "parsing", "extracting", "matching", "enriching", "scoring"];

export default function OfferListPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["offers"],
    queryFn: listOffers,
    refetchInterval: (query) => {
      const offers = (query.state.data as OfferSummary[] | undefined) ?? [];
      return offers.some((o) => ACTIVE.includes(o.status)) ? 2000 : false;
    },
  });

  return (
    <div className="space-y-8">
      <div>
        <p className="eyebrow">Eingangskanal</p>
        <h1 className="mt-1 font-display text-3xl text-investa-900">
          Maklerangebote
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-500">
          Laden Sie ein Angebot hoch. Das System extrahiert die Eckdaten, prüft
          auf Dubletten, reichert mit externen Daten an und erzeugt eine
          nachvollziehbare Bewertung von 0 bis 10.
        </p>
      </div>

      <UploadBox />

      <DashboardStats />

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50/80 text-left">
              <th className="px-5 py-3 text-[11px] font-semibold uppercase tracking-widest2 text-slate-500">
                Betreff
              </th>
              <th className="px-5 py-3 text-[11px] font-semibold uppercase tracking-widest2 text-slate-500">
                Objektart
              </th>
              <th className="px-5 py-3 text-[11px] font-semibold uppercase tracking-widest2 text-slate-500">
                Ort
              </th>
              <th className="px-5 py-3 text-[11px] font-semibold uppercase tracking-widest2 text-slate-500">
                Status
              </th>
              <th className="px-5 py-3 text-[11px] font-semibold uppercase tracking-widest2 text-slate-500">
                Bewertung
              </th>
              <th className="px-5 py-3 text-[11px] font-semibold uppercase tracking-widest2 text-slate-500">
                Empfehlung
              </th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={6} className="px-5 py-10 text-center text-slate-400">
                  Lädt …
                </td>
              </tr>
            )}
            {data?.length === 0 && (
              <tr>
                <td colSpan={6} className="px-5 py-10 text-center text-slate-400">
                  Noch keine Angebote. Laden Sie oben ein Angebot hoch.
                </td>
              </tr>
            )}
            {data?.map((o) => (
              <tr
                key={o.id}
                className="border-b border-slate-100 last:border-0 hover:bg-slate-50/70"
              >
                <td className="px-5 py-4">
                  <Link
                    to={`/offers/${o.id}`}
                    className="font-medium text-investa-700 hover:text-investa-900 hover:underline"
                  >
                    {o.subject || "(ohne Betreff)"}
                  </Link>
                  {o.is_known && (
                    <span className="ml-2 rounded-full border border-investa-300 bg-investa-500/5 px-2 py-0.5 text-[11px] uppercase tracking-wide text-investa-600">
                      bekannt
                    </span>
                  )}
                </td>
                <td className="px-5 py-4 text-slate-600">{o.objektart || "—"}</td>
                <td className="px-5 py-4 text-slate-600">{o.ort || "—"}</td>
                <td className="px-5 py-4">
                  <StatusPill status={o.status} />
                </td>
                <td className="px-5 py-4">
                  <ScoreBadge score={o.score} band={o.band} />
                </td>
                <td className="px-5 py-4 text-slate-600">{bandLabel(o.band)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const done = status === "done";
  const failed = status === "failed";
  const cls = done
    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
    : failed
      ? "bg-rose-50 text-rose-700 border-rose-200"
      : "bg-investa-500/5 text-investa-600 border-investa-200 animate-pulse";
  return (
    <span
      className={`rounded-full border px-2 py-0.5 text-[11px] uppercase tracking-wide ${cls}`}
    >
      {status}
    </span>
  );
}
