import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "./api";

afterEach(() => vi.unstubAllGlobals());

function mockFetch(handler: (url: string, init?: RequestInit) => Response | Promise<Response>) {
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => handler(url as string, init)));
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("api client", () => {
  it("returns parsed prediction on success", async () => {
    mockFetch(() => jsonResponse({ prediction: "FRAUD", risk_score: 100 }));
    const r = await api.predict({ "Sent tnx": 1 });
    expect(r.prediction).toBe("FRAUD");
  });

  it("throws ApiError with backend detail on 422", async () => {
    mockFetch(() => jsonResponse({ detail: "request validation failed" }, 422));
    await expect(api.predict({})).rejects.toMatchObject({
      status: 422,
      message: "request validation failed",
    });
  });

  it("throws a human-readable error when the backend is unreachable", async () => {
    mockFetch(() => {
      throw new TypeError("fetch failed");
    });
    await expect(api.health()).rejects.toBeInstanceOf(ApiError);
    await expect(api.health()).rejects.toMatchObject({ status: 0 });
  });

  it("sends batch uploads as multipart form data", async () => {
    let seen: RequestInit | undefined;
    mockFetch((_url, init) => {
      seen = init;
      return jsonResponse({ n_rows: 1, results: [] });
    });
    await api.predictBatch(new File(["a,b"], "t.csv", { type: "text/csv" }));
    expect(seen?.body).toBeInstanceOf(FormData);
  });
});
