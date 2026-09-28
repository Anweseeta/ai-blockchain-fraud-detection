/** Horizontal 0-100 risk score bar with labelled threshold bands. */
export function ScoreBar({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(100, score));
  return (
    <div>
      <div
        className="relative h-4 w-full overflow-hidden rounded-full bg-slate-200"
        role="img"
        aria-label={`Risk score ${score} out of 100`}
      >
        <div className="absolute inset-y-0 left-0 w-[30%] bg-emerald-300/60" />
        <div className="absolute inset-y-0 left-[30%] w-[40%] bg-amber-300/60" />
        <div className="absolute inset-y-0 left-[70%] w-[30%] bg-red-300/60" />
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-slate-800"
          style={{ width: `${pct}%`, opacity: 0.85 }}
        />
      </div>
      <div className="mt-1 flex justify-between text-xs text-slate-500" aria-hidden="true">
        <span>0 · LOW</span>
        <span>30</span>
        <span>70</span>
        <span>HIGH · 100</span>
      </div>
    </div>
  );
}
