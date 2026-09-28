import { Link } from "react-router-dom";
import { PredictionBadge, RiskBadge } from "../components/RiskBadge";
import { Card, EmptyState, ErrorAlert, Spinner, StatCard } from "../components/ui";
import { useHistory } from "../hooks";
import { fmtDate, pct, shortId } from "../utils/format";

export function Dashboard() {
  const { data, isLoading, isError, error, refetch } = useHistory(100);

  if (isLoading) return <Spinner label="Loading dashboard…" />;
  if (isError)
    return (
      <ErrorAlert
        message={error instanceof Error ? error.message : "Could not load dashboard data."}
        onRetry={() => refetch()}
      />
    );

  const records = data?.records ?? [];
  const total = records.length;
  const high = records.filter((r) => r.risk_level === "HIGH").length;
  const medium = records.filter((r) => r.risk_level === "MEDIUM").length;
  const low = records.filter((r) => r.risk_level === "LOW").length;

  const bar = (n: number, cls: string, label: string) => (
    <div>
      <div className="flex justify-between text-xs text-slate-600">
        <span>{label}</span>
        <span className="font-semibold tabular-nums">{n}</span>
      </div>
      <div className="mt-1 h-2 rounded bg-slate-200" role="img" aria-label={`${label}: ${n}`}>
        <div className={`h-2 rounded ${cls}`} style={{ width: total ? `${(n / total) * 100}%` : "0%" }} />
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <Link
          to="/analyze"
          className="rounded bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
        >
          + New analysis
        </Link>
      </div>

      {total === 0 ? (
        <EmptyState
          title="No analyses yet"
          body="Run your first analysis to see risk statistics here. Nothing is shown until the backend returns real predictions."
        />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard title="Total analyses" value={total} hint="from prediction history" />
            <StatCard title="High risk" value={high} accent="text-red-700" hint="risk score 71–100" />
            <StatCard title="Medium risk" value={medium} accent="text-amber-700" hint="risk score 31–70" />
            <StatCard title="Low risk" value={low} accent="text-emerald-700" hint="risk score 0–30" />
          </div>

          <Card title="Risk distribution">
            <div className="space-y-3">
              {bar(high, "bg-red-500", "HIGH")}
              {bar(medium, "bg-amber-400", "MEDIUM")}
              {bar(low, "bg-emerald-500", "LOW")}
            </div>
          </Card>
        </>
      )}

      <Card
        title="Recent predictions"
        aside={
          <Link to="/history" className="text-sm font-medium text-indigo-600 hover:underline">
            View all →
          </Link>
        }
      >
        {records.length === 0 ? (
          <p className="text-sm text-slate-500">No predictions recorded yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
                  <th className="py-2 pr-3">ID</th>
                  <th className="py-2 pr-3">Time</th>
                  <th className="py-2 pr-3">Prediction</th>
                  <th className="py-2 pr-3">Fraud prob.</th>
                  <th className="py-2 pr-3">Risk</th>
                </tr>
              </thead>
              <tbody>
                {records.slice(0, 10).map((r) => (
                  <tr key={r.prediction_id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="py-2 pr-3 font-mono text-xs">
                      <Link to={`/predictions/${r.prediction_id}`} state={{ record: r }} className="text-indigo-600 hover:underline">
                        {shortId(r.prediction_id)}
                      </Link>
                    </td>
                    <td className="py-2 pr-3 text-slate-600">{fmtDate(r.created_at)}</td>
                    <td className="py-2 pr-3">
                      <PredictionBadge value={r.prediction} />
                    </td>
                    <td className="py-2 pr-3 tabular-nums">{pct(r.fraud_probability)}</td>
                    <td className="py-2 pr-3">
                      <RiskBadge level={r.risk_level as "LOW" | "MEDIUM" | "HIGH"} size="sm" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
