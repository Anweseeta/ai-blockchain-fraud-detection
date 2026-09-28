import { useRef, useState } from "react";
import { PredictionBadge, RiskBadge } from "../components/RiskBadge";
import { Card, EmptyState, ErrorAlert, Spinner } from "../components/ui";
import { useBatch } from "../hooks";
import { ApiError } from "../services/api";
import type { RiskLevel } from "../types";
import { checkCsvHeaders, downloadCsv } from "../utils/csv";
import { pct } from "../utils/format";

export function Batch() {
  const batch = useBatch();
  const [fileName, setFileName] = useState<string>("");
  const [clientError, setClientError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const onFile = async (f: File | undefined) => {
    setClientError(null);
    batch.reset();
    if (!f) return;
    setFileName(f.name);
    if (!/\.csv$/i.test(f.name)) {
      setClientError("Please upload a .csv file.");
      return;
    }
    if (f.size > 5_000_000) {
      setClientError("File exceeds the 5 MB limit.");
      return;
    }
    const text = await f.text();
    const check = checkCsvHeaders(text);
    if (!check.ok) {
      setClientError(
        check.error ??
          `Missing required columns: ${check.missing.slice(0, 5).join(", ")}${
            check.missing.length > 5 ? ` (+${check.missing.length - 5} more)` : ""
          }`,
      );
      return;
    }
    batch.mutate(f);
  };

  const result = batch.data;
  const counts = result
    ? {
        HIGH: result.results.filter((r) => !r.error && r.risk_level === "HIGH").length,
        MEDIUM: result.results.filter((r) => !r.error && r.risk_level === "MEDIUM").length,
        LOW: result.results.filter((r) => !r.error && r.risk_level === "LOW").length,
      }
    : null;

  const download = () => {
    if (!result) return;
    downloadCsv(`batch_results_${Date.now()}.csv`, [
      ["row", "prediction", "fraud_probability", "risk_score", "risk_level", "error"],
      ...result.results.map((r) => [
        String(r.row),
        r.error ? "" : r.prediction,
        r.error ? "" : String(r.fraud_probability),
        r.error ? "" : String(r.risk_score),
        r.error ? "" : r.risk_level,
        r.error ?? "",
      ]),
    ]);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Batch CSV analysis</h1>
        <p className="mt-1 text-sm text-slate-600">
          Upload a CSV with the 39 model feature columns. A <code>FLAG</code> column is
          not required — and if present, it is ignored and never used for prediction.
        </p>
      </div>

      <Card title="Upload">
        <div className="flex flex-wrap items-center gap-3">
          <input
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            aria-label="Upload CSV file"
            onChange={(e) => onFile(e.target.files?.[0])}
            className="text-sm text-slate-700 file:mr-3 file:rounded file:border file:border-slate-300 file:bg-white file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-slate-50"
          />
          {fileName && <span className="text-sm text-slate-600">{fileName}</span>}
          {batch.isPending && <Spinner label="Scoring rows…" />}
        </div>
        {clientError && (
          <div role="alert" className="mt-3 rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800">
            {clientError}
          </div>
        )}
        {batch.isError && (
          <div className="mt-3">
            <ErrorAlert
              message={batch.error instanceof ApiError ? batch.error.message : "Batch scoring failed."}
              onRetry={() => inputRef.current?.click()}
            />
          </div>
        )}
      </Card>

      {result && counts && (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {[
              ["Total records", result.n_rows, "text-slate-900"],
              ["Predicted fraud", result.n_fraud, "text-red-700"],
              ["Predicted legitimate", result.n_legitimate, "text-slate-700"],
              ["Row errors", result.n_errors, "text-amber-700"],
            ].map(([t, v, c]) => (
              <div key={t as string} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t}</div>
                <div className={`mt-1 text-3xl font-bold tabular-nums ${c}`}>{v}</div>
              </div>
            ))}
          </div>

          <Card
            title="Results"
            aside={
              <button
                type="button"
                onClick={download}
                className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium hover:bg-slate-50"
              >
                Download CSV
              </button>
            }
          >
            <p className="mb-3 text-sm text-slate-600">
              Risk levels — HIGH: <strong>{counts.HIGH}</strong> · MEDIUM:{" "}
              <strong>{counts.MEDIUM}</strong> · LOW: <strong>{counts.LOW}</strong>
            </p>
            <div className="max-h-[480px] overflow-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-white">
                  <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
                    <th className="py-2 pr-3">Row</th>
                    <th className="py-2 pr-3">Prediction</th>
                    <th className="py-2 pr-3">Fraud prob.</th>
                    <th className="py-2 pr-3">Risk score</th>
                    <th className="py-2 pr-3">Risk level</th>
                    <th className="py-2 pr-3">Note</th>
                  </tr>
                </thead>
                <tbody>
                  {result.results.map((r) => (
                    <tr key={r.row} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="py-2 pr-3 tabular-nums">{r.row}</td>
                      <td className="py-2 pr-3">
                        {r.error ? <span className="text-slate-400">—</span> : <PredictionBadge value={r.prediction} />}
                      </td>
                      <td className="py-2 pr-3 tabular-nums">{r.error ? "—" : pct(r.fraud_probability)}</td>
                      <td className="py-2 pr-3 tabular-nums">{r.error ? "—" : `${r.risk_score}/100`}</td>
                      <td className="py-2 pr-3">
                        {r.error ? <span className="text-slate-400">—</span> : <RiskBadge level={r.risk_level as RiskLevel} size="sm" />}
                      </td>
                      <td className="py-2 pr-3 text-xs text-amber-700">{r.error ?? ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-3 text-xs text-slate-500">
              Predictions are statistical estimates, not proof of fraud.
            </p>
          </Card>
        </>
      )}

      {!result && !batch.isPending && (
        <EmptyState
          title="No batch results yet"
          body="Upload a CSV above. Results appear here after the backend scores each row."
        />
      )}
    </div>
  );
}
