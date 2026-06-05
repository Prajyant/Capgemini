"use client";

import { useState } from "react";
import { AgentDecision } from "@/lib/types";
import { DecisionBadge, ConfidenceBar } from "@/components/shared/StatusBadge";
import { ChevronDown, ChevronUp, Brain } from "lucide-react";
import { formatRelative } from "@/lib/utils";

export function AgentReasoningPanel({ decision }: { decision: AgentDecision }) {
  const [open, setOpen] = useState(false);
  const r = decision.full_reasoning || {};

  return (
    <div className="card border-accent/30">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-md bg-accent/15 text-accent">
            <Brain className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs uppercase tracking-wide text-textMuted">Agent Decision</div>
            <DecisionBadge decision={decision.decision_type} />
          </div>
        </div>
        <span className="text-xs text-textMuted">
          {formatRelative(decision.created_at)}
        </span>
      </div>

      <div className="bg-surface2/70 rounded-md p-3 mb-3 border-l-2 border-accent">
        <div className="text-xs uppercase tracking-wide text-accent mb-1 font-semibold">
          Plain English Summary
        </div>
        <p className="text-sm leading-relaxed">{decision.reasoning_summary}</p>
      </div>

      <div className="mb-3">
        <div className="text-xs text-textMuted mb-1">Confidence</div>
        <ConfidenceBar value={Number(decision.confidence_score)} />
      </div>

      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 text-xs text-accent hover:text-blue-400"
      >
        {open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        {open ? "Hide" : "Show"} full chain of thought
      </button>

      {open && (
        <div className="mt-4 space-y-3 text-sm border-t border-border pt-3">
          {r.signal_analysis && (
            <Section title="Signal Analysis" body={r.signal_analysis} />
          )}
          {r.situation_assessment && (
            <Section title="Situation Assessment" body={r.situation_assessment} />
          )}
          {r.options_considered && r.options_considered.length > 0 && (
            <div>
              <div className="text-xs uppercase tracking-wide text-textMuted mb-1 font-semibold">
                Options Considered
              </div>
              <ul className="space-y-1">
                {r.options_considered.map((opt: string, i: number) => (
                  <li key={i} className="text-xs leading-relaxed pl-3 border-l border-border text-textMuted">
                    {opt}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {r.email_personalisation_hooks && r.email_personalisation_hooks.length > 0 && (
            <div>
              <div className="text-xs uppercase tracking-wide text-textMuted mb-1 font-semibold">
                Personalisation Hooks
              </div>
              <div className="flex flex-wrap gap-1">
                {r.email_personalisation_hooks.map((h: string, i: number) => (
                  <span key={i} className="badge bg-accent/15 text-accent border border-accent/30">
                    {h}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Section({ title, body }: { title: string; body: string }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-textMuted mb-1 font-semibold">{title}</div>
      <p className="text-xs leading-relaxed text-textPrimary/80">{body}</p>
    </div>
  );
}
