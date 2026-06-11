"use client";

import { useEffect, useState } from "react";
import { api, SSE_URL } from "@/lib/api";
import { AgentDecision } from "@/lib/types";
import { DecisionBadge, ConfidenceBar } from "@/components/shared/StatusBadge";
import { formatRelative, leadDisplayName } from "@/lib/utils";
import { Brain, Check, X } from "lucide-react";
import Link from "next/link";

export function ActivityFeed() {
  const [decisions, setDecisions] = useState<AgentDecision[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const list = await api.listDecisions({ limit: 25 });
        setDecisions(list);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    load();

    // Connect to SSE
    let evtSource: EventSource | null = null;
    try {
      evtSource = new EventSource(SSE_URL);
      evtSource.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.type === "agent_decision") {
            // Reload to get the full decision with id
            load();
          }
        } catch {}
      };
      evtSource.onerror = () => {
        evtSource?.close();
      };
    } catch (e) {
      console.warn("SSE unavailable, falling back to polling");
    }

    const interval = setInterval(load, 8000);
    return () => {
      clearInterval(interval);
      evtSource?.close();
    };
  }, []);

  const onApprove = async (id: string) => {
    try {
      await api.approveDecision(id);
      setDecisions((prev) =>
        prev.map((d) => (d.id === id ? { ...d, was_approved: true } : d))
      );
    } catch (e) { console.error(e); }
  };

  const onOverride = async (id: string) => {
    try {
      await api.overrideDecision(id, "wait");
      setDecisions((prev) =>
        prev.map((d) => (d.id === id ? { ...d, was_approved: false } : d))
      );
    } catch (e) { console.error(e); }
  };

  return (
    <div className="card flex flex-col h-full">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-accent" />
          <h3 className="font-semibold text-sm">Live Agent Feed</h3>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-textMuted">
          <span className="w-2 h-2 bg-success rounded-full animate-pulse" />
          Live
        </div>
      </div>
      <div className="flex-1 overflow-y-auto -mx-1 px-1 max-h-[700px]">
        {loading && <div className="text-xs text-textMuted">Loading...</div>}
        {!loading && decisions.length === 0 && (
          <div className="text-xs text-textMuted text-center py-8">
            No agent decisions yet. Trigger reasoning from a lead detail page.
          </div>
        )}
        <div className="space-y-3">
          {decisions.map((d) => {
            const awaiting = d.was_approved == null && !d.executed_at;
            return (
              <div key={d.id} className="border border-border rounded-md p-3 bg-surface2/50">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <DecisionBadge decision={d.decision_type} />
                  <span className="text-[10px] text-textMuted shrink-0">
                    {formatRelative(d.created_at)}
                  </span>
                </div>
                <Link
                  href={`/leads/${d.lead_id}`}
                  className="block mb-2 group"
                >
                  <div className="text-xs font-semibold text-textPrimary group-hover:text-accent truncate">
                    {leadDisplayName(d.lead)}
                    {d.lead?.company_name && (
                      <span className="text-textMuted font-normal"> · {d.lead.company_name}</span>
                    )}
                  </div>
                  {d.lead?.job_title && (
                    <div className="text-[10px] text-textMuted truncate">{d.lead.job_title}</div>
                  )}
                </Link>
                <Link
                  href={`/leads/${d.lead_id}`}
                  className="text-xs text-textPrimary leading-relaxed hover:text-accent block mb-2"
                >
                  {d.reasoning_summary}
                </Link>
                <ConfidenceBar value={Number(d.confidence_score)} />
                {awaiting && (
                  <div className="mt-3 flex gap-2">
                    <button
                      onClick={() => onApprove(d.id)}
                      className="flex-1 btn-primary text-xs py-1 flex items-center justify-center gap-1"
                    >
                      <Check className="w-3 h-3" />
                      Approve
                    </button>
                    <button
                      onClick={() => onOverride(d.id)}
                      className="flex-1 btn-ghost text-xs py-1 flex items-center justify-center gap-1"
                    >
                      <X className="w-3 h-3" />
                      Override
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
