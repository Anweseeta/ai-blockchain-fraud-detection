import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { PredictionBadge, RiskBadge } from "../components/RiskBadge";
import { Card, EmptyState, ErrorAlert, Spinner } from "../components/ui";
import { useHistory } from "../hooks";
import type { RiskLevel } from "../types";
import { fmtDate, pct, shortId } from "../utils/format";

const PAGE_SIZE = 25;

export function History() {
  const [riskFilter, setRiskFilter] = useState<string>("");
  const [predFilter, setPredFilter] = useState<string>("");
  const [page, setPage] = useState(0);
  const { data, isLoading, isError, error, refetch } = useHistory(100);

  const filtered = useMemo(() => {
    const recs = data?.records ?? [];
    return recs.filter(
      (r) =>
        (!riskFilter || r.risk_level === riskFilter) &&
        (!predFilter || r.prediction === predFilter),
    );
  }, [data, riskFilter, predFilter]);

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageRows = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  if (isLoading) return <Spinner label="Loading history…" />;
  if (isError)
    return (
      <ErrorAlert
        message={error instanceof Error ? error.message : "Could not load prediction history."}
        onRetry={() => refetch()}
      />
    );

  const resetPage = () => setPage(0);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Prediction history</h1>

      {(data?.records.length ?? 0) === 0 ? (
        <EmptyState
          title="No predictions recorded yet"
          body="History appears here after you run analyses. The backend stores each prediction with its risk assessment and top model factors."
        />
      ) : (
        <Card title={`${filtered.length} prediction${filtered.length === 1 ? "" : "s"}`}>
          <div className="mb-4 flex flex-wrap gap-3">
            <label className="flex items-center gap-2 text-sm">
              <span className="font-medium text-slate-700">Risk level</span>
              <select
                value={riskFilter}
                onChange={(e) => {
                  setRiskFilter(e.target.value);
                  resetPage();
                }}
                className="rounded border border-slate-300 px-2 py-1.5 text-sm"
              >
                <option value="">All</option>
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LOW">LOW</option>
              </select>
            </label>
            <label className="flex items-center gap-2 text-sm">
              <span className="font-medium text-slate-700">Prediction</span>
              <select
                value={predFilter}
                onChange={(e) => {
                  setPredFilter(e.target.value);
                  resetPage();
                }}
                className="rounded border border-slate-300 px-2 py-1.5 text-sm"
              >
                <option value="">All</option>
                <option value="FRAUD">FRAUD</option>
                <option value="LEGITIMATE">LEGITIMATE</option>
              </select>
            </label>
          </div>

          {pageRows.length === 0 ? (
            <p className="text-sm text-slate-500">No predictions match these filters.</p>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
                      <th className="py-2 pr-3">ID</th>
                      <th className="py-2 pr-3">Timestamp</th>
                      <th className="py-2 pr-3">Prediction</th>
                      <th className="py-2 pr-3">Fraud prob.</th>
                      <th className="py-2 pr-3">Risk score</th>
                      <th className="py-2 pr-3">Risk level</th>
                      <th className="py-2 pr-3">Model</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pageRows.map((r) => (
                      <tr key={r.prediction_id} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="py-2 pr-3 font-mono text-xs">
                          <Link
                            to={`/predictions/${r.prediction_id}`}
                            state={{ record: r }}
                            className="text-indigo-600 hover:underline"
                          >
                            {shortId(r.prediction_id)}
                          </Link>
                        </td>
                        <td className="py-2 pr-3 text-slate-600">{fmtDate(r.created_at)}</td>
                        <td className="py-2 pr-3">
                          <PredictionBadge value={r.prediction} />
                        </td>
                        <td className="py-2 pr-3 tabular-nums">{pct(r.fraud_probability)}</td>
                        <td className="py-2 pr-3 tabular-nums">{r.risk_score}/100</td>
                        <td className="py-2 pr-3">
                          <RiskBadge level={r.risk_level as RiskLevel} size="sm" />
                        </td>
                        <td className="py-2 pr-3 text-slate-500">v{r.model_version}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-4 flex items-center justify-between text-sm">
                <span className="text-slate-600">
                  Page {page + 1} of {pages}
                </span>
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={page === 0}
                    onClick={() => setPage((p) => p - 1)}
                    className="rounded border border-slate-300 px-3 py-1 font-medium disabled:opacity-40"
                  >
                    ← Previous
                  </button>
                  <button
                    type="button"
                    disabled={page >= pages - 1}
                    onClick={() => setPage((p) => p + 1)}
                    className="rounded border border-slate-300 px-3 py-1 font-medium disabled:opacity-40"
                  >
                    Next →
                  </button>
                </div>
              </div>
            </>
          )}
        </Card>
      )}
    </div>
  );
}
