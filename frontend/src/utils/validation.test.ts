import { describe, expect, it } from "vitest";
import { FIELD_SECTIONS } from "../config/fields";
import { validateField, validateNumber, validateToken } from "./validation";

describe("validateNumber", () => {
  it("accepts ordinary numbers", () => {
    expect(validateNumber("0")).toBeNull();
    expect(validateNumber("26")).toBeNull();
    expect(validateNumber("  1.337 ")).toBeNull();
    expect(validateNumber("-5.2")).toBeNull();
    expect(validateNumber("1e6")).toBeNull();
  });
  it("rejects blanks, NaN, Infinity and garbage", () => {
    expect(validateNumber("")).not.toBeNull();
    expect(validateNumber("   ")).not.toBeNull();
    expect(validateNumber("NaN")).not.toBeNull();
    expect(validateNumber("Infinity")).not.toBeNull();
    expect(validateNumber("1e999")).not.toBeNull(); // -> Infinity
    expect(validateNumber("abc")).not.toBeNull();
    expect(validateNumber("12,34")).not.toBeNull();
    expect(validateNumber("0x10")).not.toBeNull();
  });
});

describe("validateToken", () => {
  it("accepts normal token strings", () => {
    expect(validateToken("none")).toBeNull();
    expect(validateToken("Blockwell say NOTSAFU")).toBeNull();
  });
  it("rejects blanks, overlong and hostile strings", () => {
    expect(validateToken("")).not.toBeNull();
    expect(validateToken("x".repeat(121))).not.toBeNull();
    expect(validateToken("<script>")).not.toBeNull();
    expect(validateToken('a"b')).not.toBeNull();
  });
});

describe("field coverage", () => {
  it("covers exactly 39 fields with no FLAG/Address", () => {
    const names = FIELD_SECTIONS.flatMap((s) => s.fields.map((f) => f.name));
    expect(names).toHaveLength(39);
    for (const banned of ["FLAG", "Address", "target", "label"]) {
      expect(names).not.toContain(banned);
    }
  });
  it("every field validates", () => {
    for (const s of FIELD_SECTIONS)
      for (const f of s.fields) {
        expect(validateField(f, f.kind === "number" ? "1.5" : "none")).toBeNull();
        expect(validateField(f, "")).not.toBeNull();
      }
  });
});
