import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getPreview } from "../api";
import type { DocumentOut } from "../types";

/**
 * Source-document overview: original PDF/email page thumbnails (rendered on the
 * server) plus the extracted text per document. Gives full traceability between
 * the analysis and the original material.
 */
export default function DocumentOverview({
  offerId,
  documents,
}: {
  offerId: string;
  documents: DocumentOut[];
}) {
  const [tab, setTab] = useState<"pages" | "text">("pages");
  const [zoom, setZoom] = useState<string | null>(null);

  const { data: preview, isLoading } = useQuery({
    queryKey: ["preview", offerId],
    queryFn: () => getPreview(offerId),
    staleTime: 60_000,
  });

  const textDocs = documents.filter((d) => (d.char_count ?? 0) > 0);

  return (
    <div className="card card-pad">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="card-title">Originaldokument</h2>
        <div className="flex gap-1 rounded-lg bg-slate-100 p-1 text-xs">
          <button
            onClick={() => setTab("pages")}
            className={`rounded-md px-3 py-1 ${
              tab === "pages" ? "bg-white shadow-sm text-investa-700" : "text-slate-500"
            }`}
          >
            Seiten
          </button>
          <button
            onClick={() => setTab("text")}
            className={`rounded-md px-3 py-1 ${
              tab === "text" ? "bg-white shadow-sm text-investa-700" : "text-slate-500"
            }`}
          >
            Extrahierter Text
          </button>
        </div>
      </div>

      {tab === "pages" && (
        <div>
          {isLoading && <p className="text-sm text-slate-400">Vorschau wird gerendert …</p>}
          {preview && preview.pages.length === 0 && (
            <p className="text-sm text-slate-400">
              {preview.note ?? "Keine Seitenvorschau verfügbar."}
            </p>
          )}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
            {preview?.pages.map((p, i) => (
              <button
                key={i}
                onClick={() => setZoom(p.image)}
                className="group overflow-hidden rounded-lg border border-slate-200 bg-slate-50 transition hover:border-investa-400"
                title={`${p.filename} – Seite ${p.page}`}
              >
                <img
                  src={p.image}
                  alt={`${p.filename} Seite ${p.page}`}
                  className="h-44 w-full object-cover object-top transition group-hover:scale-[1.02]"
                  loading="lazy"
                />
                <div className="truncate px-2 py-1 text-left text-[10px] text-slate-500">
                  {p.filename} · S.{p.page}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {tab === "text" && (
        <div className="space-y-4">
          {textDocs.length === 0 && (
            <p className="text-sm text-slate-400">Kein extrahierter Text vorhanden.</p>
          )}
          {textDocs.map((d) => (
            <details key={d.id} className="rounded-lg border border-slate-200" open>
              <summary className="cursor-pointer px-3 py-2 text-sm font-medium text-investa-700">
                {d.filename}{" "}
                <span className="font-normal text-slate-400">
                  ({d.doc_type}, {d.char_count.toLocaleString("de-DE")} Zeichen)
                </span>
              </summary>
              <pre className="max-h-80 overflow-auto whitespace-pre-wrap px-3 pb-3 text-xs leading-relaxed text-slate-700">
                {d.extracted_text}
              </pre>
            </details>
          ))}
        </div>
      )}

      {zoom && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-6"
          onClick={() => setZoom(null)}
        >
          <img
            src={zoom}
            alt="Seitenansicht"
            className="max-h-full max-w-3xl rounded-lg shadow-2xl"
          />
        </div>
      )}
    </div>
  );
}
