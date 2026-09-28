/** TypeScript types mirroring the FastAPI schemas (backend/app/schemas/). */

export type Prediction = "FRAUD" | "LEGITIMATE";
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH";
export type Direction = "increases_risk" | "decreases_risk";

/** 39 raw model input features, keyed by exact backend field name. */
export type PredictRequest = Record<string, number | string>;

export interface ShapFactor {
  feature: string;
  value: string;
  shap_value: number;
  direction: Direction;
  explanation_type: "model_contribution";
}

export interface PredictionResponse {
  prediction: Prediction;
  fraud_probability: number;
  risk_score: number;
  risk_level: RiskLevel;
  threshold: number;
  top_factors: ShapFactor[];
  prediction_id: string;
  model_version: string;
}

export interface BatchItem {
  row: number;
  prediction: Prediction;
  fraud_probability: number;
  risk_score: number;
  risk_level: RiskLevel;
  error: string | null;
}

export interface BatchResponse {
  n_rows: number;
  n_fraud: number;
  n_legitimate: number;
  n_errors: number;
  results: BatchItem[];
  model_version: string;
}

export interface ExplainResponse {
  fraud_probability: number;
  prediction: string;
  top_factors: ShapFactor[];
  note: string;
}

export interface HealthResponse {
  status: string;
  artifacts_loaded: boolean;
  database: "connected" | "disabled" | "degraded";
  model_version: string;
}

export interface ModelInfoResponse {
  model_type: string;
  model_version: string;
  n_features: number;
  threshold: number;
  risk_weights: Record<string, number>;
  risk_thresholds: Record<string, number>;
  risk_config_version: string;
  shap_explainer: string;
}

export interface HistoryRecord {
  prediction_id: string;
  created_at: string;
  model_version: string;
  threshold: number;
  prediction: string;
  fraud_probability: number;
  risk_score: number;
  risk_level: string;
  top_factors: ShapFactor[];
}

export interface HistoryResponse {
  n: number;
  records: HistoryRecord[];
}
