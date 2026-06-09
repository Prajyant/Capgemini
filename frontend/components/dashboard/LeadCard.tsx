"use client";

import Link from "next/link";
import { Lead, AgentDecision } from "@/lib/types";
import { formatRelative } from "@/lib/utils";
import { Brain, ChevronRight, Clock } from "lucide-react";
import { StateBadge, DecisionBadge, ConfidenceBar } from "@/components/shared/StatusBadge";

export function LeadCard({
  lead, latestDecision,
}: {
  lead: Lead;
  latestDecision?: AgentDecision;
}) {
  const fullName = `${lead.first_name || ""} ${lead.last_name || ""}`.trim() || lead.email;
  const company = lead.company?.name || "—";
  const initials = fullName
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <Link
      href={`/leads/${lead.id}`}
      className="block group bg-surface border border-border rounded-lg p-3 hover:border-accent/60 hover:bg-surface2/50 transition-all"
    >
      {/* Name row */}
      <div className="flex items-start gap-2.5 mb-2">
        {/* Avatar */}
        <div className="w-8 h-8 rounded-full bg-accent/20 text-accent text-xs font-bold flex items-center justify-center shrink-0">
          {initials || "?"}
        </div>
        <div className="min-w-0 flex-1">
          <div className="font-semibold text-sm text-textPrimary truncate leading-tight">{fullName}</div>
          <div className="text-xs text-textMuted truncate leading-tight mt-0.5">
            {lead.job_title || "Unknown role"}
          </div>
          <div className="text-xs text-textMuted truncate">{company}</div>
        </div>
        <ChevronRight className="w-3.5 h-3.5 text-textMuted group-hover:text-accent transition shrink-0 mt-1" />
      </div>

      {/* Scores row */}
      <div className="flex items-center gap-2 mb-2">
        <StateBadge state={lead.state} />
        <div className="ml-auto flex items-center gap-1.5">
          <div className="text-[10px] text-textMuted">enrichment</div>
          <div className="text-xs font-bold tabular-nums text-textPrimary">
            {lead.enrichment_score}<span className="text-textMuted text-[10px]">/100</span>
          </div>
        </div>
      </div>

      {/* Agent decision */}
      {latestDecision && (
        <div className="mt-2 pt-2 border-t border-border/40">
          <div className="flex items-center gap-1.5 mb-1">
            <Brain className="w-3 h-3 text-accent shrink-0" />
            <DecisionBadge decision={latestDecision.decision_type} />
          </div>
          <p className="text-[11px] text-textMuted leading-relaxed line-clamp-2">
            {latestDecision.reasoning_summary}
          </p>
          <div className="mt-1.5">
            <ConfidenceBar value={Number(latestDecision.confidence_score)} />
          </div>
        </div>
      )}

      {/* Next action */}
      {lead.next_action_at && (
        <div className="flex items-center gap-1 mt-2 text-[10px] text-textMuted">
          <Clock className="w-3 h-3" />
          <span>Next action: {formatRelative(lead.next_action_at)}</span>
        </div>
      )}
    </Link>
  );
}
