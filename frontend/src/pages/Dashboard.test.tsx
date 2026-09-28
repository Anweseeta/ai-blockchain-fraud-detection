import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Dashboard } from "../pages/Dashboard";

afterEach(() => vi.unstubAllGlobals());

function setup(fetchImpl: () => Promise<Response>) {
  vi.stubGlobal("fetch", vi.fn(fetchImpl));
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Dashboard states", () => {
  it("shows a human-readable error when the backend is unreachable", async () => {
    setup(() => {
      throw new TypeError("fetch failed");
    });
    expect(await screen.findByRole("alert", undefined, { timeout: 5000 })).toHaveTextContent(/could not reach the api/i);
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });

  it("shows an empty state instead of fake numbers when there is no history", async () => {
    setup(() => Promise.resolve(new Response(JSON.stringify({ n: 0, records: [] }), { status: 200 })));
    expect(await screen.findByText(/no analyses yet/i)).toBeInTheDocument();
    expect(screen.queryByText(/total analyses/i)).not.toBeInTheDocument();
  });

  it("renders real counts from the history endpoint", async () => {
    const records = [
      { prediction_id: "a1", created_at: "2026-09-25T10:00:00+00:00", model_version: "1.0.0", threshold: 0.55, prediction: "FRAUD", fraud_probability: 0.9, risk_score: 90, risk_level: "HIGH", top_factors: [] },
      { prediction_id: "b2", created_at: "2026-09-25T10:01:00+00:00", model_version: "1.0.0", threshold: 0.55, prediction: "LEGITIMATE", fraud_probability: 0.1, risk_score: 10, risk_level: "LOW", top_factors: [] },
    ];
    setup(() => Promise.resolve(new Response(JSON.stringify({ n: 2, records }), { status: 200 })));
    expect(await screen.findByText("Total analyses")).toBeInTheDocument();
    // total=2 rendered as the stat value
    expect(screen.getByText("High risk").parentElement).toHaveTextContent("1");
  });
});
