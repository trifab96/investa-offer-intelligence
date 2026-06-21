/**
 * Lightweight map preview using OpenStreetMap's embeddable iframe — no API key,
 * no extra dependency. Shows a marker at the geocoded position.
 */
export default function MapCard({
  lat,
  lon,
  label,
}: {
  lat: number;
  lon: number;
  label?: string | null;
}) {
  const d = 0.012;
  const bbox = `${lon - d}%2C${lat - d}%2C${lon + d}%2C${lat + d}`;
  const src = `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${lat}%2C${lon}`;
  const link = `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=16/${lat}/${lon}`;

  return (
    <div className="card overflow-hidden">
      <div className="card-pad pb-3">
        <h2 className="card-title">Lage</h2>
        {label && <p className="mt-1 text-xs text-slate-500">{label}</p>}
      </div>
      <iframe
        title="Standort"
        className="h-72 w-full border-0"
        loading="lazy"
        src={src}
      />
      <div className="card-pad py-2 text-right">
        <a
          href={link}
          target="_blank"
          rel="noreferrer"
          className="text-xs text-investa-600 hover:text-investa-800"
        >
          Größere Karte öffnen ({lat.toFixed(4)}, {lon.toFixed(4)}) →
        </a>
      </div>
    </div>
  );
}
