import { cn, STATE_COLORS, DECISION_COLORS, DECISION_LABELS } from "@/lib/utils";

export function StateBadge({ state }: { state: string }) {
  return (
    <span
      className={cn(
        "badge border",
        STATE_COLORS[state] || "bg-slate-500/20 text-slate-300 border-slate-500/40"
      )}
    >
      {state}
    </span>
  );
}

export function DecisionBadge({ decision }: { decision: string }) {
  return (
    <span
      className={cn(
        "badge border",
        DECISION_COLORS[decision] || "bg-slate-500/20 text-slate-300 border-slate-500/40"
      )}
    >
      {DECISION_LABELS[decision] || decision}
    </span>
  );
}

export function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    value >= 0.85 ? "bg-success" : value >= 0.65 ? "bg-accent" : "bg-warning";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-surface2 rounded-full overflow-hidden min-w-[60px]">
        <div className={cn("h-full transition-all", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-textMuted w-10 text-right">{pct}%</span>
    </div>
  );
}
