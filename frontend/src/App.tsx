import { Link, Outlet, useLocation } from "react-router-dom";

const NAV = [
  { to: "/", label: "Angebote" },
  { to: "/compare", label: "Vergleich" },
];

export default function App() {
  const location = useLocation();
  const isActive = (to: string) =>
    to === "/" ? location.pathname === "/" : location.pathname.startsWith(to);

  return (
    <div className="flex min-h-screen flex-col">
      <header className="bg-investa-800 text-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <Link to="/" className="flex items-baseline gap-3">
            <span className="font-display text-2xl font-semibold tracking-tight">
              INVESTA
            </span>
            <span className="hidden text-[11px] font-medium uppercase tracking-widest2 text-investa-300 sm:inline">
              Offer Intelligence
            </span>
          </Link>
          <nav className="flex items-center gap-8">
            {NAV.map((n) => (
              <Link
                key={n.to}
                to={n.to}
                className={`text-[12px] uppercase tracking-widest2 transition-colors ${
                  isActive(n.to)
                    ? "text-white"
                    : "text-investa-300 hover:text-white"
                }`}
              >
                {n.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="h-px bg-white/10" />
      </header>

      <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-10">
        <Outlet />
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-2 px-6 py-6 text-xs text-slate-500 sm:flex-row sm:items-center">
          <span>
            Investa Offer Intelligence · KI Challenge Prototyp · Forward Deployed
            Engineer
          </span>
          <span className="uppercase tracking-widest2 text-investa-500">
            KI-gestützte Angebotsbewertung
          </span>
        </div>
      </footer>
    </div>
  );
}
