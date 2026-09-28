import type { RiskLevel } from "../types";

const STYLES: Record<RiskLevel, { badge: string; icon: string; label: string }> = {
  HIGH: {
    badge: "bg-red-100 text-red-800 border-red-300",
    icon: "▲",
    label: "High risk",
  },
  MEDIUM: {
    badge: "bg-amber-100 text-amber-800 border-amber-300",
    icon: "◆",
    label: "Medium risk",
  },
  LOW: {
    badge: "bg-emerald-100 text-emerald-800 border-emerald-300",
    icon: "●",
    label: "Low risk",
  },
};

/** Risk badge: icon + text, never color alone. */
export function RiskBadge({ level, size = "md" }: { level: RiskLevel; size?: "sm" | "md" | "lg" }) {
  const s = STYLES[level];
  const pad = size === "lg" ? "px-4 py-2 text-base" : size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm";
  return (
    <span
      role="status"
      aria-label={s.label}
      className={`inline-flex items-center gap-1.5 rounded-full border font-semibold ${s.badge} ${pad}`}
    >
      <span aria-hidden="true">{s.icon}</span>
      {level}
    </span>
  );
}

export function PredictionBadge({ value }: { value: string }) {
  const fraud = value === "FRAUD";
  return (
    <span
      role="status"
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-semibold ${
        fraud
          ? "border-red-300 bg-red-100 text-red-800"
          : "border-slate-300 bg-slate-100 text-slate-700"
      }`}
    >
      <span aria-hidden="true">{fraud ? "⚑" : "✓"}</span>
      {fraud ? "FRAUD" : "LEGITIMATE"}
    </span>
  );
}
