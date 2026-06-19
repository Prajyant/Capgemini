"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { AgentDecision } from "@/lib/types";
import { AgentReasoningPanel } from "@/components/dashboard/AgentReasoningPanel";

/**
 * Renders the agent's chain-of-thought timeline for one lead.
 *
 * The "Compose Email" entry point lives at the top of the lead detail page
 * (always visible), so we no longer duplicate it inline here.
 *
 * `onApprove` / `onOverride` are forwarded to the latest decision card so
 * presenters can approve or override the agent's recommendation directly
 * from the chain of thought.
 */
export function LeadStateTimeline({
  decisions,
  onApprove,
  onOverride,
}: {
  decisions: AgentDecision[];
  onApprove?: (id: string) => Promise<void> | void;
  onOverride?: (id: string) => Promise<void> | void;
  // Kept on the type for backwards compatibility; unused now.
  leadId?: string;
  leadEmail?: string;
  onEmailSent?: () => void;
}) {
  const [showOlder, setShowOlder] = useState(false);

  if (!decisions || decisions.length === 0) {
    return (
      <div className="card text-center text-textMuted py-8">
        No agent reasoning history for this lead yet.
      </div>
    );
  }

  // decisions arrive newest-first from the API
  const latest = decisions[0];
  const older = decisions.slice(1);

  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-sm flex items-center gap-2">
        <span className="w-1 h-4 bg-accent rounded-full" />
        Latest Decision
      </h3>

      <div className="relative pl-4 border-l border-border">
        <div className="relative">
          <div className="absolute -left-[21px] top-3 w-3 h-3 rounded-full bg-accent border-2 border-bg" />
          <AgentReasoningPanel
            decision={latest}
            onApprove={onApprove}
            onOverride={onOverride}
          />
        </div>
      </div>

      {older.length > 0 && (
        <div>
          <button
            onClick={() => setShowOlder(!showOlder)}
            className="flex items-center gap-1 text-xs text-accent hover:text-blue-400 mb-3"
          >
            {showOlder ? (
              <ChevronUp className="w-3 h-3" />
            ) : (
              <ChevronDown className="w-3 h-3" />
            )}
            {showOlder
              ? "Hide older decisions"
              : `View ${older.length} older decision${older.length > 1 ? "s" : ""}`}
          </button>

          {showOlder && (
            <div className="relative pl-4 border-l border-border space-y-4 opacity-80">
              {older.map((d) => (
                <div key={d.id} className="relative">
                  <div className="absolute -left-[21px] top-3 w-3 h-3 rounded-full bg-textMuted/40 border-2 border-bg" />
                  <AgentReasoningPanel decision={d} />
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
