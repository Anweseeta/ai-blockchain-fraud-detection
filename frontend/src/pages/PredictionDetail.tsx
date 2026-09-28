import { Link, useLocation, useParams } from "react-router-dom";
import { PredictionBadge, RiskBadge } from "../components/RiskBadge";
import { ScoreBar } from "../components/ScoreBar";
import { ShapChart } from "../components/ShapChart";
import { Card, EmptyState, ErrorAlert, Spinner } from "../components/ui";
import { useHistory } from "../hooks";
import type { HistoryRecord, PredictionResponse, RiskLevel, ShapFactor } from "../types";
import { fmtDate, pct, shortId } from "../utils/format";

interface ViewModel {
  prediction: string;
  fraud_probability: number;
  risk_score: number;
  risk_level: RiskLevel;
  threshold: number;
  top_factors: ShapFactor[];
  prediction_id: string;
  model_version: string;
  created_at?: string;
}

function fromResponse(r: PredictionResponse): ViewModel {
  return { ...r, risk_level: r.risk_level };
}

function fromRecord(r: HistoryRecord): ViewModel {
  return {
    prediction: r.prediction,
    fraud_probability: r.fraud_probability,
    risk_score: r.risk_score,
    risk_level: r.risk_level as RiskLevel,
    threshold: r.threshold,
    top_factors: r.top_factors,
    prediction_id: r.prediction_id,
    model_version: r.model_version,
    created_at: r.created_at,
  };
}

export function PredictionDetail() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const stateResp = (location.state as { response?: PredictionResponse } | null)?.response;

  const { data, isLoading, isError, error, refetch } = useHistory(100);

  let vm: ViewModel | null = stateResp ? fromResponse(stateResp) : null;
  if (!vm && data) {
    const rec = data.records.find((r) => r.prediction_id === id);
    if (rec) vm = fromRecord(rec);
  }

  if (!stateResp && isLoading) return <Spinner label="Loading prediction…" />;
  if (!stateResp && isError)
    return (
      <ErrorAlert
        message={error instanceof Error ? error.message : "Could not load this prediction."}
        onRetry={() => refetch()}
      />
    );
  if (!vm)
    return (
      <EmptyState
        title="Prediction not found"
        body="This prediction ID is not in the recent history. It may have aged out of the stored list."
      />
    );

  const fraud = vm.prediction === "FRAUD";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Prediction result</h1>
          <p className="mt-1 font-mono text-xs text-slate-500">
            {shortId(vm.prediction_id)} · model v{vm.model_version}
            {vm.created_at && ` · ${fmtDate(vm.created_at)}`}
          </p>
        </div>
        <Link to="/analyze" className="rounded border border-slate-300 bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50">
          New analysis
        </Link>
      </div>

      <Card title="Model output">
        <div className="grid gap-6 md:grid-cols-2">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <PredictionBadge value={vm.prediction} />
              <RiskBadge level={vm.risk_level} size="lg" />
            </div>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between border-b border-slate-100 py-1">
                <dt className="text-slate-600">Fraud probability</dt>
                <dd className="font-semibold tabular-nums">{pct(vm.fraud_probability)}</dd>
              </div>
              <div className="flex justify-between border-b border-slate-100 py-1">
                <dt className="text-slate-600">Risk score</dt>
                <dd className="font-semibold tabular-nums">{vm.risk_score} / 100</dd>
              </div>
              <div className="flex justify-between border-b border-slate-100 py-1">
                <dt className="text-slate-600">Operating threshold</dt>
                <dd className="font-semibold tabular-nums">{vm.threshold}</dd>
              </div>
              <div className="flex justify-between py-1">
                <dt className="text-slate-600">Decision rule</dt>
                <dd className="text-slate-800">
                  p ≥ {vm.threshold} → FRAUD
                </dd>
              </div>
            </dl>
          </div>
          <div>
            <p className="mb-2 text-sm font-medium text-slate-700">Risk score</p>
            <ScoreBar score={vm.risk_score} />
            <div
              className={`mt-4 rounded-lg border p-4 text-sm ${
                fraud ? "border-red-200 bg-red-50 text-red-900" : "border-slate-200 bg-slate-50 text-slate-700"
              }`}
              role="note"
            >
              <p className="font-semibold">
                {fraud
                  ? "The model classifies this account as fraud-like."
                  : "The model classifies this account as legitimate-like."}
              </p>
              <p className="mt-1">
                This is a statistical model prediction ({pct(vm.fraud_probability)} fraud
                probability), <strong>not proof of fraud</strong>. Treat it as one input
                to human review, alongside independent evidence.
              </p>
            </div>
          </div>
        </div>
      </Card>

      <Card title="Model explanation — factors contributing to this prediction">
        <p className="mb-2 text-sm text-slate-600">
          These SHAP values show how much each feature moved <em>this model's</em> output.
          They describe model contribution, <strong>not causation</strong> — a feature
          increasing the prediction does not prove it causes fraud.
        </p>
        <ShapChart factors={vm.top_factors} />
      </Card>
    </div>
  );
}
