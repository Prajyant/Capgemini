"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { AgentDecision } from "@/lib/types";
import { AgentReasoningPanel } from "@/components/dashboard/AgentReasoningPanel";
import { EmailComposer } from "@/components/leads/EmailComposer";

export function LeadStateTimeline({
  decisions,
  leadId,
  leadEmail,
  onEmailSent,
}: {
  decisions: AgentDecision[];
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
  const showEmailComposer =
    latest.decision_type === "send_email" && leadId && leadEmail;

  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-sm flex items-center gap-2">
        <span className="w-1 h-4 bg-accent rounded-full" />
        Latest Decision
      </h3>

      <div className="relative pl-4 border-l border-border">
        <div className="relative">
          <div className="absolute -left-[21px] top-3 w-3 h-3 rounded-full bg-accent border-2 border-bg" />
          <AgentReasoningPanel decision={latest} />
        </div>
      </div>

      {/* Email composer appears when the agent recommends sending an email */}
      {showEmailComposer && (
        <div className="card border-accent/30 bg-accent/5">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div className="text-sm text-textMuted">
              The agent recommends sending an email. Review and send a
              personalized draft below.
            </div>
            <EmailComposer
              leadId={leadId!}
              leadEmail={leadEmail!}
              onSent={onEmailSent}
            />
          </div>
        </div>
      )}

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
