"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Lead, AgentDecision } from "@/lib/types";
import { LeadCard } from "./LeadCard";

const COLUMNS = [
  { state: "new", label: "New", accent: "text-slate-300" },
  { state: "enriched", label: "Enriched", accent: "text-cyan-300" },
  { state: "contacted", label: "Contacted", accent: "text-blue-300" },
  { state: "engaged", label: "Engaged", accent: "text-purple-300" },
  { state: "replied", label: "Replied", accent: "text-emerald-300" },
  { state: "converted", label: "Converted", accent: "text-success" },
];

export function PipelineBoard() {
  const [leadsByState, setLeadsByState] = useState<Record<string, Lead[]>>({});
  const [decisionsByLead, setDecisionsByLead] = useState<Record<string, AgentDecision>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [allLeads, recentDecisions] = await Promise.all([
          api.listLeads({ limit: 200 }),
          api.listDecisions({ limit: 200 }),
        ]);
        const grouped: Record<string, Lead[]> = {};
        for (const col of COLUMNS) grouped[col.state] = [];
        for (const lead of allLeads) {
          if (grouped[lead.state]) grouped[lead.state].push(lead);
        }
        setLeadsByState(grouped);

        const decMap: Record<string, AgentDecision> = {};
        for (const d of recentDecisions) {
          if (!decMap[d.lead_id]) decMap[d.lead_id] = d;
        }
        setDecisionsByLead(decMap);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    load();
    const i = setInterval(load, 12000);
    return () => clearInterval(i);
  }, []);

  if (loading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
        {COLUMNS.map((c) => (
          <div key={c.state} className="card animate-pulse h-72" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
      {COLUMNS.map((col) => {
        const leads = leadsByState[col.state] || [];
        return (
          <div key={col.state} className="bg-surface/50 rounded-lg border border-border flex flex-col">
            <div className="px-3 py-2 border-b border-border flex items-center justify-between">
              <div className={`text-xs font-semibold uppercase tracking-wide ${col.accent}`}>
                {col.label}
              </div>
              <div className="text-xs text-textMuted">{leads.length}</div>
            </div>
            <div className="p-2 space-y-2 flex-1 overflow-y-auto max-h-[350px]">
              {leads.length === 0 && (
                <div className="text-xs text-textMuted text-center py-4">
                  No leads
                </div>
              )}
              {leads.map((lead) => (
                <LeadCard
                  key={lead.id}
                  lead={lead}
                  latestDecision={decisionsByLead[lead.id]}
                />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
