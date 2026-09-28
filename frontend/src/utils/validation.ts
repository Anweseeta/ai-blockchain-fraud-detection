/** Client-side validation mirroring backend rules. */
import type { ModelField } from "../config/fields";

export function validateNumber(raw: string): string | null {
  const t = raw.trim();
  if (t === "") return "Required";
  // reject hex, exponents are fine; Number() handles the rest
  if (!/^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/.test(t))
    return "Enter a valid number";
  const v = Number(t);
  if (!Number.isFinite(v)) return "Must be a finite number";
  if (Math.abs(v) > 1e18) return "Value is unrealistically large";
  return null;
}

export function validateToken(raw: string): string | null {
  const t = raw.trim();
  if (t === "") return "Required";
  if (t.length > 120) return "Must be 120 characters or fewer";
  if (/[<>"'\\]/.test(t)) return "Contains invalid characters";
  return null;
}

export function validateField(field: ModelField, raw: string): string | null {
  return field.kind === "number" ? validateNumber(raw) : validateToken(raw);
}

/** Parse a validated numeric string. Returns null when invalid. */
export function parseNumber(raw: string): number | null {
  return validateNumber(raw) === null ? Number(raw.trim()) : null;
}
