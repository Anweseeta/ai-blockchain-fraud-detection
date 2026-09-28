/** Centralized API client. All backend calls go through here. */
import { API_PREFIX, API_URL } from "../config";
import type {
  BatchResponse,
  ExplainResponse,
  HealthResponse,
  HistoryResponse,
  ModelInfoResponse,
  PredictionResponse,
  PredictRequest,
} from "../types";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${API_PREFIX}${path}`, init);
  } catch {
    throw new ApiError(0, "Could not reach the API. Is the backend running?");
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* keep default */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

const jsonHeaders = { "Content-Type": "application/json" };

export const api = {
  predict(payload: PredictRequest): Promise<PredictionResponse> {
    return request<PredictionResponse>("/predict", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify(payload),
    });
  },

  explain(payload: PredictRequest, topK = 10): Promise<ExplainResponse> {
    return request<ExplainResponse>(`/explain?top_k=${topK}`, {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify(payload),
    });
  },

  predictBatch(file: File): Promise<BatchResponse> {
    const form = new FormData();
    form.append("file", file);
    return request<BatchResponse>("/predict/batch", { method: "POST", body: form });
  },

  predictions(limit = 100, riskLevel?: string): Promise<HistoryResponse> {
    const q = new URLSearchParams({ limit: String(limit) });
    if (riskLevel) q.set("risk_level", riskLevel);
    return request<HistoryResponse>(`/predictions?${q.toString()}`);
  },

  health(): Promise<HealthResponse> {
    return request<HealthResponse>("/health");
  },

  modelInfo(): Promise<ModelInfoResponse> {
    return request<ModelInfoResponse>("/model-info");
  },
};
