/** Minimal CSV helpers: header validation + result download. */
import { FIELD_NAMES } from "../config/fields";

export function parseCsvHeaders(text: string): string[] {
  const firstLine = text.split(/\r?\n/)[0] ?? "";
  // exact header names: the backend requires the 39 columns verbatim
  // (several begin with a space), so only strip surrounding quotes here.
  return firstLine.split(",").map((h) => h.replace(/^"|"$/g, "").replace(/\r$/, ""));
}

export interface CsvCheck {
  ok: boolean;
  missing: string[];
  error?: string;
}

/** Check that a CSV's header contains all 39 model features. */
export function checkCsvHeaders(text: string): CsvCheck {
  const headers = parseCsvHeaders(text);
  if (headers.length < 2 && headers[0] === "")
    return { ok: false, missing: [], error: "File appears to be empty." };
  const missing = FIELD_NAMES.filter((f) => !headers.includes(f));
  return { ok: missing.length === 0, missing };
}

export function downloadCsv(filename: string, rows: string[][]): void {
  const esc = (c: string) => (/[",\n]/.test(c) ? `"${c.replace(/"/g, '""')}"` : c);
  const text = rows.map((r) => r.map(esc).join(",")).join("\n");
  const blob = new Blob([text], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
