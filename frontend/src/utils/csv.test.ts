import { describe, expect, it } from "vitest";
import { FIELD_NAMES } from "../config/fields";
import { checkCsvHeaders } from "./csv";

describe("checkCsvHeaders", () => {
  it("accepts a header with all 39 features (extras allowed)", () => {
    const text = [...FIELD_NAMES, "FLAG", "Address"].join(",") + "\n1,2,3";
    const c = checkCsvHeaders(text);
    expect(c.ok).toBe(true);
    expect(c.missing).toHaveLength(0);
  });
  it("rejects a header missing features", () => {
    const text = FIELD_NAMES.slice(0, 30).join(",") + "\n1,2,3";
    const c = checkCsvHeaders(text);
    expect(c.ok).toBe(false);
    expect(c.missing).toHaveLength(9);
  });
  it("rejects empty input", () => {
    expect(checkCsvHeaders("").ok).toBe(false);
  });
});
