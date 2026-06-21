import { useState } from "react";
import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { getOffer } from "../api";
import type { Driver, OfferDetail, PromptTrace, SubScore } from "../types";
import ScoreGauge from "../components/ScoreGauge";
import ScoreBadge from "../components/ScoreBadge";
import MapCard from "../components/MapCard";
import DocumentOverview from "../components/DocumentOverview";

const ACTIVE = ["received", "parsing", "extracting", "matching", "enriching", "scoring"];

export default function OfferDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading } = useQuery({
    queryKey: ["offer", id],
    queryFn: () => getOffer(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const o = query.state.data as OfferDetail | undefined;
      return o && ACTIVE.includes(o.status) ? 2000 : false;
    },
  });

  if (isLoading || !data) return <p className="text-slate-400">Lädt …</p>;

  return (
    <div className="space-y-6">
      <Link
        to="/"
        className="text-[12px] uppercase tracking-widest2 text-investa-500 hover:text-investa-700"
      >
        ← Zurück zur Übersicht
      </Link>

      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow">Angebot</p>
          <h1 className="mt-1 font-display text-3xl text-investa-900">
            {data.subject || "(ohne Betreff)"}
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            Status: <span className="font-medium text-slate-700">{data.status}</span>
            {data.is_known && (
              <span className="ml-2 rounded-full border border-investa-300 bg-investa-500/5 px-2 py-0.5 text-[11px] uppercase tracking-wide text-investa-600">
                Objekt bereits bekannt
              </span>
            )}
          </p>
          {data.error && (
            <p className="text-rose-600 text-sm mt-1">Fehler: {data.error}</p>
          )}
        </div>
        {data.score != null && (
          <ScoreBadge score={data.score} band={data.band} />
        )}
      </div>

      {data.is_known && data.replies.length > 0 && (
        <KnownReply reply={data.replies[0]} />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <ExtractionCard extraction={data.extraction} />
        <EnrichmentCard enrichment={data.enrichment} />
        <ScoreCard detail={data} />
      </div>

      {data.enrichment?.geo?.lat != null && data.enrichment?.geo?.lon != null && (
        <MapCard
          lat={data.enrichment.geo.lat}
          lon={data.enrichment.geo.lon}
          label={data.enrichment.geo.display_name}
        />
      )}

      {data.scoring?.top_drivers && data.scoring.top_drivers.length > 0 && (
        <TopDrivers drivers={data.scoring.top_drivers} />
      )}

      {data.enrichment?.image_analysis && (
        <ImageAnalysisCard analysis={data.enrichment.image_analysis} />
      )}

      {data.scoring && (data.scoring.rationale || data.scoring.risks || data.scoring.opportunities) && (
        <RisksOpportunities
          risks={data.scoring.risks}
          opportunities={data.scoring.opportunities}
          rationale={data.scoring.rationale}
        />
      )}

      {data.prompt_trace && <PromptTracePanel traces={data.prompt_trace} />}

      {data.documents.length > 0 && (
        <DocumentOverview offerId={data.id} documents={data.documents} />
      )}
    </div>
  );
}

function TopDrivers({ drivers }: { drivers: Driver[] }) {
  return (
    <div className="card card-pad">
      <h2 className="card-title mb-1">Wichtigste Treiber der Bewertung</h2>
      <p className="mb-4 text-xs text-slate-500">
        Die Faktoren mit dem größten Einfluss auf den Score (gewichtete Abweichung
        vom neutralen Mittel).
      </p>
      <div className="space-y-3">
        {drivers.map((d) => {
          const pct = Math.min(100, Math.abs(d.impact) * 60);
          const positive = d.direction === "positive";
          return (
            <div key={d.name}>
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium text-slate-700">
                  <span
                    className={`mr-2 inline-block ${
                      positive ? "text-emerald-600" : "text-rose-600"
                    }`}
                  >
                    {positive ? "▲" : "▼"}
                  </span>
                  {subLabel(d.name)}
                </span>
                <span
                  className={`tabular-nums text-xs font-semibold ${
                    positive ? "text-emerald-700" : "text-rose-700"
                  }`}
                >
                  {positive ? "+" : ""}
                  {d.impact.toFixed(2)}
                </span>
              </div>
              {d.detail && (
                <p className="mt-0.5 text-xs text-slate-500">{d.detail}</p>
              )}
              <div className="mt-1 h-1.5 rounded-full bg-slate-100">
                <div
                  className={`h-1.5 rounded-full ${
                    positive ? "bg-emerald-500" : "bg-rose-500"
                  }`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ImageAnalysisCard({ analysis }: { analysis: Record<string, any> }) {
  const lists: [string, string[]][] = [
    ["Auffälligkeiten", analysis.auffaelligkeiten ?? []],
    ["Visuelle Risiken", analysis.visuelle_risiken ?? []],
    ["Visuelle Chancen", analysis.visuelle_chancen ?? []],
  ];
  return (
    <div className="card card-pad">
      <h2 className="card-title mb-1">Bildanalyse (KI-Vision)</h2>
      <p className="mb-4 text-xs text-slate-500">
        {analysis.images_analyzed ?? 0} Bild(er) analysiert · Konfidenz{" "}
        {analysis.confidence != null
          ? `${Math.round(analysis.confidence * 100)}%`
          : "—"}
      </p>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <dl className="space-y-1.5 text-sm">
          <Row k="Bildtypen" v={(analysis.bildtypen ?? []).join(", ") || null} />
          <Row k="Objekt" v={analysis.objekt_sichtbar} />
          <Row k="Zustand (visuell)" v={analysis.zustand_visuell} />
          <Row k="Umgebung" v={analysis.umgebung} />
        </dl>
        <div className="space-y-3">
          {lists.map(([label, items]) =>
            items.length ? (
              <div key={label}>
                <p className="text-[11px] font-semibold uppercase tracking-widest2 text-slate-500">
                  {label}
                </p>
                <ul className="list-inside list-disc text-sm text-slate-600">
                  {items.map((it, i) => (
                    <li key={i}>{it}</li>
                  ))}
                </ul>
              </div>
            ) : null,
          )}
        </div>
      </div>
    </div>
  );
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="card card-pad">
      <h2 className="card-title mb-4">{title}</h2>
      {children}
    </div>
  );
}

function ExtractionCard({ extraction }: { extraction: Record<string, any> | null }) {
  if (!extraction)
    return <Card title="Extraktion">Keine Daten</Card>;
  const lage = extraction.lage || {};
  const groesse = extraction.groesse || {};
  const preis = extraction.kaufpreis || {};
  const rows: [string, any][] = [
    ["Objektart", extraction.objektart],
    ["Ort", lage.ort],
    ["PLZ", lage.plz],
    ["Straße", lage.strasse],
    ["Grundstück (m²)", groesse.grundstueck_m2],
    ["Wohnfläche (m²)", groesse.wohnflaeche_m2],
    ["Einheiten", groesse.einheiten],
    ["Kaufpreis", preis.betrag ? `${fmt(preis.betrag)} ${preis.waehrung || "EUR"}` : null],
    ["Zustand", extraction.zustand],
    ["Baujahr", extraction.baujahr],
    ["Konfidenz", extraction.confidence != null ? `${Math.round(extraction.confidence * 100)}%` : null],
  ];
  return (
    <Card title="Extrahierte Fakten">
      <dl className="space-y-1.5 text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-4">
            <dt className="text-slate-500">{k}</dt>
            <dd className="font-medium text-right">{v ?? "—"}</dd>
          </div>
        ))}
      </dl>
      {Array.isArray(extraction.nutzungsmoeglichkeiten) &&
        extraction.nutzungsmoeglichkeiten.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1.5">
            {extraction.nutzungsmoeglichkeiten.map((u: string) => (
              <span
                key={u}
                className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-xs text-slate-600"
              >
                {u}
              </span>
            ))}
          </div>
        )}
    </Card>
  );
}

function EnrichmentCard({ enrichment }: { enrichment: Record<string, any> | null }) {
  if (!enrichment) return <Card title="Anreicherung">Keine Daten</Card>;
  const geo = enrichment.geo || {};
  const poi = enrichment.poi || {};
  const demo = enrichment.demographics || {};
  const rent = enrichment.rent_benchmark || {};
  return (
    <Card title="Externe Anreicherung">
      <dl className="space-y-1.5 text-sm">
        <Row k="Koordinaten" v={geo.lat ? `${geo.lat.toFixed(4)}, ${geo.lon.toFixed(4)}` : null} />
        <Row k="Adresse (Geo)" v={geo.display_name} />
        <Row k="Einwohner" v={demo.population ? fmt(demo.population) : null} />
        <Row k="POIs (1 km)" v={poi.total} />
        <Row
          k="Referenzmiete €/m²"
          v={rent.reference_rent_eur_m2_month}
        />
        <Row k="Referenzpreis €/m²" v={rent.reference_buy_price_eur_m2 ? fmt(rent.reference_buy_price_eur_m2) : null} />
      </dl>
      {enrichment.sources && (
        <p className="mt-3 text-xs text-slate-400">
          Quellen: {(enrichment.sources as string[]).join(", ")}
        </p>
      )}
    </Card>
  );
}

function ScoreCard({ detail }: { detail: OfferDetail }) {
  const subscores: SubScore[] = detail.scoring?.subscores ?? [];
  const metrics = detail.scoring?.metrics ?? {};
  const label = detail.scoring?.asset_class_label;
  const penalty = detail.scoring?.risk_penalty ?? 0;
  if (detail.score == null)
    return <Card title="Bewertung">Noch keine Bewertung (oder bekanntes Objekt).</Card>;
  return (
    <Card title="Bewertung">
      {label && (
        <div className="mb-3 flex justify-center">
          <span className="rounded-full border border-investa-300 bg-investa-500/5 px-3 py-0.5 text-[11px] uppercase tracking-widest2 text-investa-600">
            Bewertet als: {label}
          </span>
        </div>
      )}
      <div className="flex justify-center">
        <ScoreGauge score={detail.score} />
      </div>
      <div className="mt-5 space-y-2.5">
        {subscores.map((s) => (
          <div key={s.name}>
            <div className="flex justify-between text-xs text-slate-500">
              <span>
                {subLabel(s.name)}{" "}
                <span className="opacity-60">
                  ({s.kind}, w={s.weight})
                </span>
              </span>
              <span className="font-medium tabular-nums text-slate-700">
                {s.value.toFixed(1)}
              </span>
            </div>
            <div className="mt-1 h-1.5 rounded-full bg-slate-100">
              <div
                className="h-1.5 rounded-full bg-investa-500"
                style={{ width: `${(s.value / 10) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
      {Object.keys(metrics).length > 0 && (
        <div className="mt-5 space-y-1 border-t border-slate-100 pt-4 text-xs text-slate-500">
          {Object.entries(metrics).map(([k, v]) => (
            <div key={k} className="flex justify-between">
              <span>{k}</span>
              <span className="font-medium tabular-nums text-slate-700">
                {String(v)}
              </span>
            </div>
          ))}
        </div>
      )}
      {penalty > 0 && (
        <div className="mt-3 flex justify-between border-t border-slate-100 pt-3 text-xs">
          <span className="font-medium text-rose-600">Risikoabzug</span>
          <span className="font-semibold tabular-nums text-rose-700">
            −{penalty.toFixed(2)}
          </span>
        </div>
      )}
    </Card>
  );
}

const SUB_LABELS: Record<string, string> = {
  location: "Lage",
  occupancy: "Vermietungsstand",
  reversion: "Mietsteigerungspotenzial",
  buildability: "Bebaubarkeit / Potenzial",
  price_vs_market: "Preis vs. Markt",
  condition: "Zustand",
  size_usage: "Größe / Nutzung",
  data_completeness: "Datenvollständigkeit",
  risk_penalty: "Risikoabzug",
};

function subLabel(name: string): string {
  return SUB_LABELS[name] ?? name;
}

function RisksOpportunities({
  risks,
  opportunities,
  rationale,
}: {
  risks?: string[] | null;
  opportunities?: string[] | null;
  rationale: string | null;
}) {
  const risksList = risks ?? [];
  const opportunitiesList = opportunities ?? [];
  return (
    <div className="card card-pad">
      <h2 className="card-title mb-4">Einschätzung</h2>
      {rationale && (
        <p className="mb-5 text-sm leading-relaxed text-slate-600">{rationale}</p>
      )}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <div>
          <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-widest2 text-rose-600">
            Risiken
          </h3>
          <ul className="list-inside list-disc space-y-1 text-sm text-slate-600">
            {risksList.length ? risksList.map((r, i) => <li key={i}>{r}</li>) : <li>—</li>}
          </ul>
        </div>
        <div>
          <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-widest2 text-emerald-600">
            Chancen
          </h3>
          <ul className="list-inside list-disc space-y-1 text-sm text-slate-600">
            {opportunitiesList.length
              ? opportunitiesList.map((o, i) => <li key={i}>{o}</li>)
              : <li>—</li>}
          </ul>
        </div>
      </div>
    </div>
  );
}

function KnownReply({ reply }: { reply: { subject: string | null; body: string | null } }) {
  return (
    <div className="rounded-lg border-l-4 border-investa-500 bg-investa-500/[0.04] p-6">
      <p className="eyebrow">Antwortentwurf an den Makler · nicht versendet</p>
      <p className="mt-2 font-display text-lg text-investa-800">{reply.subject}</p>
      <pre className="mt-3 whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-700">
        {reply.body}
      </pre>
    </div>
  );
}

function PromptTracePanel({ traces }: { traces: PromptTrace[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="card card-pad">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 card-title"
      >
        Prompt-Trace ({traces.length}) {open ? "▼" : "▶"}
        <span className="text-[11px] font-normal normal-case tracking-normal text-slate-400">
          Nachvollziehbares Prompt Engineering
        </span>
      </button>
      {open && (
        <div className="mt-4 space-y-4">
          {traces.map((t, i) => (
            <details key={i} className="rounded-lg border border-slate-200 p-3">
              <summary className="cursor-pointer text-sm font-medium text-investa-700">
                {t.purpose} — {t.model}
              </summary>
              <div className="mt-2 space-y-2 text-xs">
                <TraceBlock label="System" text={t.system} />
                <TraceBlock label="User" text={t.user} />
                <TraceBlock label="Params" text={JSON.stringify(t.params, null, 2)} />
                <TraceBlock label="Raw response" text={t.raw_response ?? ""} />
              </div>
            </details>
          ))}
        </div>
      )}
    </div>
  );
}

function TraceBlock({ label, text }: { label: string; text: string }) {
  return (
    <div>
      <p className="text-slate-400 uppercase tracking-wide">{label}</p>
      <pre className="whitespace-pre-wrap rounded bg-slate-50 p-2 text-slate-700 max-h-48 overflow-auto">
        {text}
      </pre>
    </div>
  );
}

function Row({ k, v }: { k: string; v: any }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-slate-500">{k}</dt>
      <dd className="font-medium text-right">{v ?? "—"}</dd>
    </div>
  );
}

function fmt(n: number): string {
  return new Intl.NumberFormat("de-DE").format(n);
}
