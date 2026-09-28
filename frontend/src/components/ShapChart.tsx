import { useState } from "react";
import type { ShapFactor } from "../types";
import { fmtNum } from "../utils/format";

/**
 * Horizontal SHAP contribution chart.
 * Uses the actual SHAP response — nothing is fabricated.
 * Clearly labelled as model contribution, not causation.
 */
export function ShapChart({ factors }: { factors: ShapFactor[] }) {
  const [active, setActive] = useState<number | null>(null);
  const maxAbs = Math.max(0.0001, ...factors.map((f) => Math.abs(f.shap_value)));

  const inc = factors.filter((f) => f.direction === "increases_risk");
  const dec = factors.filter((f) => f.direction === "decreases_risk");

  const renderGroup = (
    title: string,
    items: ShapFactor[],
    barClass: string,
    emptyNote: string,
  ) => (
    <section aria-label={title} className="mt-6">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
        {title} <span className="font-normal text-slate-400">({items.length})</span>
      </h3>
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-slate-500">{emptyNote}</p>
      ) : (
        <ul className="mt-2 space-y-1.5">
          {items.map((f) => {
            const gi = factors.indexOf(f);
            const width = (Math.abs(f.shap_value) / maxAbs) * 100;
            return (
              <li key={`${f.feature}-${gi}`}>
                <button
                  type="button"
                  onMouseEnter={() => setActive(gi)}
                  onMouseLeave={() => setActive(null)}
                  onFocus={() => setActive(gi)}
                  onBlur={() => setActive(null)}
                  onClick={() => setActive(active === gi ? null : gi)}
                  aria-expanded={active === gi}
                  className="block w-full rounded px-2 py-1 text-left hover:bg-slate-100 focus:bg-slate-100"
                >
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="truncate text-sm font-medium text-slate-800">
                      {f.feature.trim()}
                    </span>
                    <span className="shrink-0 font-mono text-xs text-slate-500">
                      {f.shap_value > 0 ? "+" : ""}
                      {f.shap_value.toFixed(3)}
                    </span>
                  </div>
                  <div className="mt-1 h-2.5 w-full rounded bg-slate-200">
                    <div
                      className={`h-2.5 rounded ${barClass}`}
                      style={{ width: `${width}%` }}
                      role="img"
                      aria-label={`${f.feature.trim()}: SHAP ${f.shap_value.toFixed(3)}`}
                    />
                  </div>
                  {active === gi && (
                    <dl className="mt-1.5 rounded border border-slate-200 bg-white p-2 text-xs text-slate-600 shadow-sm">
                      <div className="flex justify-between gap-2">
                        <dt className="font-semibold">Feature</dt>
                        <dd className="text-right">{f.feature.trim()}</dd>
                      </div>
                      <div className="flex justify-between gap-2">
                        <dt className="font-semibold">Input value</dt>
                        <dd className="text-right font-mono">{fmtNum(f.value)}</dd>
                      </div>
                      <div className="flex justify-between gap-2">
                        <dt className="font-semibold">SHAP contribution</dt>
                        <dd className="text-right font-mono">
                          {f.shap_value > 0 ? "+" : ""}
                          {f.shap_value.toFixed(5)} log-odds
                        </dd>
                      </div>
                      <div className="flex justify-between gap-2">
                        <dt className="font-semibold">Direction</dt>
                        <dd className="text-right">
                          {f.direction === "increases_risk"
                            ? "Increased the model's fraud prediction"
                            : "Decreased the model's fraud prediction"}
                        </dd>
                      </div>
                    </dl>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );

  return (
    <div>
      {renderGroup(
        "Factors increasing the model's fraud prediction",
        inc,
        "bg-red-500",
        "No factors pushed the prediction upward.",
      )}
      {renderGroup(
        "Factors decreasing the model's fraud prediction",
        dec,
        "bg-indigo-500",
        "No factors pushed the prediction downward.",
      )}
      <p className="mt-4 text-xs text-slate-500">
        SHAP values are in log-odds units and show how much each feature moved this
        model's output — model contribution, not causation.
      </p>
    </div>
  );
}
