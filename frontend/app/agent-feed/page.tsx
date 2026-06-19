"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { AgentDecision } from "@/lib/types";
import { DecisionBadge, ConfidenceBar } from "@/components/shared/StatusBadge";
import { AgentReasoningPanel } from "@/components/dashboard/AgentReasoningPanel";
import { formatRelative } from "@/lib/utils";
import { Building2, Check, Filter, User, X } from "lucide-react";

const DECISION_FILTERS = [
  "", "send_email", "send_linkedin_dm", "suggest_call", "wait", "escalate_to_human", "close_sequence",
];

export default function AgentFeedPage() {
  const [decisions, setDecisions] = useState<AgentDecision[]>([]);
  const [filter, setFilter] = useState("");
  const [minConf, setMinConf] = useState("");
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { limit: 100 };
      if (filter) params.decision_type = filter;
      if (minConf) params.min_confidence = parseFloat(minConf);
      const list = await api.listDecisions(params);
      setDecisions(list);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [filter, minConf]);

  useEffect(() => {
    load();
  }, [load]);

  const onApprove = async (id: string) => {
    try {
      await api.approveDecision(id);
      setDecisions((prev) =>
        prev.map((d) => (d.id === id ? { ...d, was_approved: true } : d))
      );
    } catch (e) {
      console.error(e);
    }
  };

  const onOverride = async (id: string) => {
    try {
      await api.overrideDecision(id, "wait");
      setDecisions((prev) =>
        prev.map((d) => (d.id === id ? { ...d, was_approved: false } : d))
      );
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold mb-1">Agent Reasoning Feed</h1>
        <p className="text-sm text-textMuted">
          Full audit log of every decision the agent has made. This is the transparency layer.
        </p>
      </div>

      <div className="card flex flex-wrap items-center gap-3">
        <Filter className="w-4 h-4 text-textMuted" />
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="bg-surface2 border border-border rounded px-2 py-1 text-sm"
        >
          {DECISION_FILTERS.map((f) => (
            <option key={f} value={f}>{f || "All decisions"}</option>
          ))}
        </select>
        <select
          value={minConf}
          onChange={(e) => setMinConf(e.target.value)}
          className="bg-surface2 border border-border rounded px-2 py-1 text-sm"
        >
          <option value="">Any confidence</option>
          <option value="0.85">≥ 85% (high)</option>
          <option value="0.65">≥ 65% (medium+)</option>
          <option value="0.0">All</option>
        </select>
        <span className="text-xs text-textMuted ml-auto">
          {decisions.length} decisions
        </span>
      </div>

      {loading && <div className="text-textMuted text-sm">Loading...</div>}

      <div className="space-y-3">
        {decisions.map((d) => {
          const awaiting = d.was_approved == null && !d.executed_at;
          return (
            <div key={d.id} className="card">
              <div className="flex items-start justify-between gap-3 mb-2 flex-wrap">
                <div className="flex items-center gap-2 flex-wrap">
                  <DecisionBadge decision={d.decision_type} />
                  {d.was_approved === true && (
                    <span className="badge bg-success/15 text-success border border-success/30">approved</span>
                  )}
                  {d.was_approved === false && (
                    <span className="badge bg-danger/15 text-danger border border-danger/30">overridden</span>
                  )}
                  {awaiting && (
                    <span className="badge bg-warning/15 text-warning border border-warning/30">awaiting</span>
                  )}
                </div>
                <Link href={`/leads/${d.lead_id}`} className="text-xs text-accent hover:underline">
                  View lead
                </Link>
              </div>

              {(d.lead_name || d.lead_company) && (
                <Link
                  href={`/leads/${d.lead_id}`}
                  className="flex items-center gap-3 text-xs mb-2 hover:text-accent w-fit"
                >
                  {d.lead_name && (
                    <span className="flex items-center gap-1 text-textPrimary font-medium">
                      <User className="w-3 h-3 text-textMuted" />
                      {d.lead_name}
                    </span>
                  )}
                  {d.lead_company && (
                    <span className="flex items-center gap-1 text-textMuted">
                      <Building2 className="w-3 h-3" />
                      {d.lead_company}
                    </span>
                  )}
                </Link>
              )}

              <p className="text-sm leading-relaxed mb-3">{d.reasoning_summary}</p>
              <div className="flex items-center gap-4">
                <div className="flex-1">
                  <ConfidenceBar value={Number(d.confidence_score)} />
                </div>
                <span className="text-xs text-textMuted shrink-0">
                  {formatRelative(d.created_at)}
                </span>
              </div>

              {awaiting && (
                <div className="mt-3 flex gap-2">
                  <button
                    onClick={() => onApprove(d.id)}
                    className="btn-primary text-xs py-1 px-3 flex items-center gap-1"
                  >
                    <Check className="w-3 h-3" />
                    Approve
                  </button>
                  <button
                    onClick={() => onOverride(d.id)}
                    className="btn-ghost text-xs py-1 px-3 flex items-center gap-1"
                  >
                    <X className="w-3 h-3" />
                    Override
                  </button>
                </div>
              )}

              <button
                onClick={() => setExpanded(expanded === d.id ? null : d.id)}
                className="mt-3 text-xs text-accent hover:underline"
              >
                {expanded === d.id ? "Hide" : "Show"} full reasoning
              </button>
              {expanded === d.id && (
                <div className="mt-3">
                  <AgentReasoningPanel decision={d} />
                </div>
              )}
            </div>
          );
        })}
        {!loading && decisions.length === 0 && (
          <div className="card text-center text-textMuted py-12">
            No decisions match your filters.
          </div>
        )}
      </div>
    </div>
  );
}
