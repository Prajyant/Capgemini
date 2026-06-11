"use client";

import Link from "next/link";
import { Lead, AgentDecision } from "@/lib/types";
import { formatRelative } from "@/lib/utils";
import { Brain, ChevronRight } from "lucide-react";

export function LeadCard({
  lead, latestDecision,
}: {
  lead: Lead;
  latestDecision?: AgentDecision;
}) {
  const fullName = `${lead.first_name || ""} ${lead.last_name || ""}`.trim() || lead.email;
  const company = lead.company?.name || "—";

  return (
    <Link
      href={`/leads/${lead.id}`}
      className="card card-hover block group"
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="min-w-0 flex-1">
          <div className="font-semibold text-sm truncate">{fullName}</div>
          <div className="text-xs text-textMuted truncate">
            {lead.job_title || "—"} · {company}
          </div>
        </div>
        <div className="shrink-0 flex flex-col items-end gap-1">
          <div className="text-xs font-bold tabular-nums">
            {lead.enrichment_score}
            <span className="text-textMuted text-[10px] ml-0.5">/100</span>
          </div>
          <div className="text-[10px] text-textMuted">enrichment</div>
        </div>
      </div>

      {latestDecision && (
        <div className="mt-2 pt-2 border-t border-border/50">
          <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-accent font-medium mb-0.5">
            <Brain className="w-3 h-3" />
            Agent decided
          </div>
          <div className="text-[11px] text-textMuted line-clamp-1 leading-relaxed">
            {latestDecision.reasoning_summary}
          </div>
        </div>
      )}

      <div className="mt-3 flex items-center justify-between text-[10px] text-textMuted">
        <span>
          {lead.next_action_at
            ? (() => {
                const d = new Date(lead.next_action_at);
                return d.getTime() < Date.now()
                  ? "Action due now"
                  : `Next: ${formatRelative(lead.next_action_at)}`;
              })()
            : "No action scheduled"}
        </span>
        <ChevronRight className="w-3 h-3 group-hover:text-accent transition" />
      </div>
    </Link>
  );
}
