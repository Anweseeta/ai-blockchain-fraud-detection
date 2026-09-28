import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../services/api";
import type { PredictRequest } from "../types";

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    retry: 1,
    refetchInterval: 30000,
  });
}

export function useModelInfo() {
  return useQuery({ queryKey: ["model-info"], queryFn: api.modelInfo, retry: 1 });
}

export function useHistory(limit = 100, riskLevel?: string) {
  return useQuery({
    queryKey: ["predictions", limit, riskLevel ?? ""],
    queryFn: () => api.predictions(limit, riskLevel),
    retry: 1,
  });
}

export function usePredict() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: PredictRequest) => api.predict(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["predictions"] }),
  });
}

export function useBatch() {
  return useMutation({ mutationFn: (file: File) => api.predictBatch(file) });
}
