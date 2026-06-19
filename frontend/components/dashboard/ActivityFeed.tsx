"use client";

import { useEffect, useState } from "react";
import { api, SSE_URL } from "@/lib/api";
import { AgentDecision } from "@/lib/types";
import { DecisionBadge, ConfidenceBar } from "@/components/shared/StatusBadge";
import { formatRelative } from "@/lib/utils";
import { Brain, Building2, Check, X, User } from "lucide-react";
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

    // SSE drives the live updates; the interval is a slow safety net so
    // missed events get reconciled within 30s without hammering the API.
    const interval = setInterval(load, 30000);
    return () => {
      clearInterval(interval);
      evtSource?.close();
    };
  }, []);

  const onApprove = async (id: string) => {
    try {
      await api.approveDecision(id);
      setDecisions((prev) =>
        prev.map((d) => (d.id === id ? { ...d, was_approved: true, approved_by: "human" } : d))
      );
    } catch (e: any) {
      console.error(e);
      alert(`Approve failed: ${e?.message || e}`);
    }
  };

  const onOverride = async (id: string) => {
    try {
      await api.overrideDecision(id, "wait");
      setDecisions((prev) =>
        prev.map((d) => (d.id === id ? { ...d, was_approved: false, approved_by: "human_override" } : d))
      );
    } catch (e: any) { console.error(e); }
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
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
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

                {/* Who is this decision about — always visible so the
                    presenter knows what they're approving / overriding. */}
                {(d.lead_name || d.lead_company) && (
                  <Link
                    href={`/leads/${d.lead_id}`}
                    className="flex items-center gap-2 text-xs mb-1.5 hover:text-accent"
                  >
                    {d.lead_name && (
                      <span className="flex items-center gap-1 text-textPrimary font-medium truncate">
                        <User className="w-3 h-3 text-textMuted shrink-0" />
                        {d.lead_name}
                      </span>
                    )}
                    {d.lead_company && (
                      <span className="flex items-center gap-1 text-textMuted truncate">
                        <Building2 className="w-3 h-3 shrink-0" />
                        {d.lead_company}
                      </span>
                    )}
                  </Link>
                )}

                <Link
                  href={`/leads/${d.lead_id}`}
                  className="text-xs text-textMuted leading-relaxed hover:text-accent block mb-2"
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
                {d.was_approved === true && (
                  <div className="mt-2 text-[11px] text-success flex items-center gap-1">
                    <Check className="w-3 h-3" />
                    Approved
                  </div>
                )}
                {d.was_approved === false && (
                  <div className="mt-2 text-[11px] text-danger flex items-center gap-1">
                    <X className="w-3 h-3" />
                    Overridden
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
