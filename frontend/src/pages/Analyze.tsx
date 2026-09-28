import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FIELD_SECTIONS, type ModelField } from "../config/fields";
import { SAMPLE_INPUTS } from "../config/samples";
import { Card, ErrorAlert } from "../components/ui";
import { usePredict } from "../hooks";
import { ApiError } from "../services/api";
import type { PredictRequest } from "../types";
import { parseNumber, validateField } from "../utils/validation";

function FieldInput({
  field,
  value,
  error,
  onChange,
}: {
  field: ModelField;
  value: string;
  error: string | null;
  onChange: (v: string) => void;
}) {
  const id = `field-${field.name}`;
  const inputCls = `w-full rounded border px-3 py-1.5 text-sm ${
    error ? "border-red-400 bg-red-50" : "border-slate-300"
  }`;
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-slate-700">
        {field.label}
      </label>
      {field.kind === "number" ? (
        <input
          id={id}
          type="text"
          inputMode="decimal"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="0"
          aria-invalid={!!error}
          aria-describedby={error ? `${id}-err` : field.help ? `${id}-help` : undefined}
          className={inputCls}
        />
      ) : (
        <input
          id={id}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="none"
          maxLength={120}
          aria-invalid={!!error}
          aria-describedby={error ? `${id}-err` : field.help ? `${id}-help` : undefined}
          className={inputCls}
        />
      )}
      {field.help && !error && (
        <p id={`${id}-help`} className="mt-0.5 text-xs text-slate-500">
          {field.help}
        </p>
      )}
      {error && (
        <p id={`${id}-err`} role="alert" className="mt-0.5 text-xs font-medium text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}

export function Analyze() {
  const navigate = useNavigate();
  const predict = usePredict();
  const [values, setValues] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState(false);

  const errors = useMemo(() => {
    const out: Record<string, string> = {};
    for (const s of FIELD_SECTIONS)
      for (const f of s.fields) {
        const e = validateField(f, values[f.name] ?? "");
        if (e) out[f.name] = e;
      }
    return out;
  }, [values]);

  const set = (name: string, v: string) => setValues((p) => ({ ...p, [name]: v }));

  const fillSample = (key: "fraudLike" | "legitLike") => {
    const s = SAMPLE_INPUTS[key];
    setValues(Object.fromEntries(Object.entries(s.values).map(([k, v]) => [k, String(v)])));
    setTouched(false);
  };

  const clear = () => {
    setValues({});
    setTouched(false);
    predict.reset();
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setTouched(true);
    if (Object.keys(errors).length > 0) return;
    const payload: PredictRequest = {};
    for (const s of FIELD_SECTIONS)
      for (const f of s.fields)
        payload[f.name] =
          f.kind === "number" ? (parseNumber(values[f.name] ?? "") as number) : (values[f.name] ?? "").trim();
    predict.mutate(payload, {
      onSuccess: (resp) =>
        navigate(`/predictions/${resp.prediction_id}`, { state: { response: resp } }),
    });
  };

  const nErrors = Object.keys(errors).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">New analysis</h1>
          <p className="mt-1 text-sm text-slate-600">
            Enter the account's transaction aggregates. The model's target label (FLAG) and
            address are <strong>not</strong> inputs and cannot influence the prediction.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => fillSample("fraudLike")}
            className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium hover:bg-slate-50"
          >
            Fill fraud-like example
          </button>
          <button
            type="button"
            onClick={() => fillSample("legitLike")}
            className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium hover:bg-slate-50"
          >
            Fill legitimate-like example
          </button>
          <button
            type="button"
            onClick={clear}
            className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium hover:bg-slate-50"
          >
            Clear
          </button>
        </div>
      </div>

      {touched && nErrors > 0 && (
        <div role="alert" className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800">
          <p className="font-semibold">Please fix {nErrors} field{nErrors === 1 ? "" : "s"} before submitting.</p>
        </div>
      )}

      {predict.isError && (
        <ErrorAlert
          message={
            predict.error instanceof ApiError
              ? predict.error.message
              : "Prediction failed. Please try again."
          }
          onRetry={() => predict.reset()}
        />
      )}

      <form onSubmit={submit} noValidate>
        <div className="space-y-6">
          {FIELD_SECTIONS.map((s) => (
            <Card key={s.id} title={`${s.title} (${s.fields.length} fields)`}>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {s.fields.map((f) => (
                  <FieldInput
                    key={f.name}
                    field={f}
                    value={values[f.name] ?? ""}
                    error={touched ? errors[f.name] ?? null : null}
                    onChange={(v) => set(f.name, v)}
                  />
                ))}
              </div>
            </Card>
          ))}
        </div>

        <div className="sticky bottom-0 mt-6 flex items-center justify-between gap-4 rounded-lg border border-slate-200 bg-white/95 p-4 shadow-sm backdrop-blur">
          <p className="text-sm text-slate-600">
            {nErrors === 0
              ? "All 39 fields valid. Submitting runs the real backend model."
              : `${nErrors} field${nErrors === 1 ? "" : "s"} need${nErrors === 1 ? "s" : ""} attention.`}
          </p>
          <button
            type="submit"
            disabled={predict.isPending}
            className="rounded bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {predict.isPending ? "Scoring…" : "Run prediction"}
          </button>
        </div>
      </form>
    </div>
  );
}
