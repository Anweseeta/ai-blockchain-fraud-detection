import { NavLink, Outlet } from "react-router-dom";
import { useHealth } from "../hooks";

const LINKS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/analyze", label: "New analysis" },
  { to: "/batch", label: "Batch CSV" },
  { to: "/history", label: "History" },
  { to: "/status", label: "System status" },
];

export function AppLayout() {
  const { data: health } = useHealth();
  const dbOk = health?.database === "connected";
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-slate-900 text-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4 px-4 py-3">
          <div className="mr-4">
            <p className="text-base font-bold tracking-tight">Fraud Risk Console</p>
            <p className="text-xs text-slate-400">Blockchain transaction anomaly review</p>
          </div>
          <nav aria-label="Primary" className="flex flex-wrap gap-1">
            {LINKS.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.end}
                className={({ isActive }) =>
                  `rounded px-3 py-1.5 text-sm font-medium ${
                    isActive ? "bg-slate-700 text-white" : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2 text-xs" role="status">
            <span
              aria-hidden="true"
              className={`inline-block h-2.5 w-2.5 rounded-full ${dbOk ? "bg-emerald-400" : "bg-amber-400"}`}
            />
            <span className="text-slate-300">
              API {health ? (health.artifacts_loaded ? "ready" : "degraded") : "…"}
              {health && ` · DB ${health.database}`}
            </span>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
      <footer className="mx-auto max-w-6xl px-4 pb-8 text-xs text-slate-500">
        Model predictions are statistical estimates, not proof of fraud. Explanations show
        model contribution, not causation.
      </footer>
    </div>
  );
}
