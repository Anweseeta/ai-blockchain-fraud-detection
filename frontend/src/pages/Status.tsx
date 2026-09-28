import { Card, ErrorAlert, Spinner } from "../components/ui";
import { useHealth, useModelInfo } from "../hooks";

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-4 border-b border-slate-100 py-2 text-sm last:border-0">
      <dt className="text-slate-600">{k}</dt>
      <dd className="text-right font-medium text-slate-900">{v}</dd>
    </div>
  );
}

export function Status() {
  const health = useHealth();
  const info = useModelInfo();

  if (health.isLoading || info.isLoading) return <Spinner label="Checking system status…" />;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">System status</h1>

      {health.isError && (
        <ErrorAlert
          message={
            health.error instanceof Error
              ? health.error.message
              : "The backend is unreachable."
          }
          onRetry={() => health.refetch()}
        />
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <Card title="API health">
          {health.data ? (
            <dl>
              <Row
                k="API status"
                v={
                  <span className={`font-semibold ${health.data.status === "ok" ? "text-emerald-700" : "text-amber-700"}`}>
                    {health.data.status === "ok" ? "● Operational" : "● Degraded"}
                  </span>
                }
              />
              <Row k="Model artifacts" v={health.data.artifacts_loaded ? "Loaded" : "Missing"} />
              <Row
                k="Database"
                v={
                  <span className={health.data.database === "connected" ? "text-emerald-700" : "text-amber-700"}>
                    {health.data.database}
                  </span>
                }
              />
              <Row k="Model version" v={`v${health.data.model_version}`} />
            </dl>
          ) : (
            <p className="text-sm text-slate-500">No health data — backend unreachable.</p>
          )}
        </Card>

        <Card title="Model information">
          {info.isError ? (
            <p className="text-sm text-slate-500">Model metadata unavailable.</p>
          ) : info.data ? (
            <dl>
              <Row k="Model type" v={info.data.model_type} />
              <Row k="Model version" v={`v${info.data.model_version}`} />
              <Row k="Input features" v={info.data.n_features} />
              <Row k="Operating threshold" v={info.data.threshold} />
              <Row
                k="Risk weights"
                v={`fraud ${info.data.risk_weights.fraud_probability}, anomaly ${info.data.risk_weights.anomaly_score}`}
              />
              <Row
                k="Risk bands"
                v={`LOW ≤ ${info.data.risk_thresholds.low_max}, MEDIUM ≤ ${info.data.risk_thresholds.medium_max}, HIGH above`}
              />
              <Row k="Explainer" v={info.data.shap_explainer} />
            </dl>
          ) : null}
        </Card>
      </div>

      <Card title="About this system">
        <div className="space-y-2 text-sm text-slate-600">
          <p>
            Predictions come from a validated XGBoost classifier (threshold{" "}
            {info.data?.threshold ?? "—"}) applied to 39 account-level transaction
            features. A risk score of 0–100 is derived from the fraud probability.
          </p>
          <p>
            Explanations use SHAP values: they show how much each feature moved the
            model's output for one account — model contribution, not causation, and
            never proof of fraud.
          </p>
        </div>
      </Card>
    </div>
  );
}
