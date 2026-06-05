"use client";

import { AgentDecision } from "@/lib/types";
import { AgentReasoningPanel } from "@/components/dashboard/AgentReasoningPanel";

export function LeadStateTimeline({
  decisions,
}: {
  decisions: AgentDecision[];
}) {
  if (!decisions || decisions.length === 0) {
    return (
      <div className="card text-center text-textMuted py-8">
        No agent reasoning history for this lead yet.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-sm flex items-center gap-2">
        <span className="w-1 h-4 bg-accent rounded-full" />
        Engagement Timeline
      </h3>
      <div className="relative pl-4 border-l border-border space-y-4">
        {decisions.map((d) => (
          <div key={d.id} className="relative">
            <div className="absolute -left-[21px] top-3 w-3 h-3 rounded-full bg-accent border-2 border-bg" />
            <AgentReasoningPanel decision={d} />
          </div>
        ))}
      </div>
    </div>
  );
}
