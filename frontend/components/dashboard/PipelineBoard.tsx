"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Lead, AgentDecision } from "@/lib/types";
import { LeadCard } from "./LeadCard";
import { Search, RefreshCw } from "lucide-react";

const COLUMNS = [
  { state: "new",       label: "New",       accent: "text-slate-300",   dot: "bg-slate-400" },
  { state: "enriched",  label: "Enriched",  accent: "text-cyan-300",    dot: "bg-cyan-400" },
  { state: "contacted", label: "Contacted", accent: "text-blue-300",    dot: "bg-blue-400" },
  { state: "engaged",   label: "Engaged",   accent: "text-purple-300",  dot: "bg-purple-400" },
  { state: "replied",   label: "Replied",   accent: "text-emerald-300", dot: "bg-emerald-400" },
  { state: "converted", label: "Converted", accent: "text-success",     dot: "bg-success" },
];

export function PipelineBoard() {
  const [leadsByState, setLeadsByState] = useState<Record<string, Lead[]>>({});
  const [decisionsByLead, setDecisionsByLead] = useState<Record<string, AgentDecision>>({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState("");

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
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
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
    const i = setInterval(() => load(true), 15000);
    return () => clearInterval(i);
  }, [load]);

  const filterLeads = (leads: Lead[]) => {
    if (!search.trim()) return leads;
    const q = search.toLowerCase();
    return leads.filter((l) =>
      (l.first_name || "").toLowerCase().includes(q) ||
      (l.last_name || "").toLowerCase().includes(q) ||
      (l.email || "").toLowerCase().includes(q) ||
      (l.company?.name || "").toLowerCase().includes(q)
    );
  };

  const totalLeads = Object.values(leadsByState).reduce((sum, arr) => sum + arr.length, 0);

  if (loading) {
    return (
      <div className="space-y-3">
        <div className="h-9 bg-surface2 animate-pulse rounded-lg w-72" />
        <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
          {COLUMNS.map((c) => (
            <div key={c.state} className="card animate-pulse h-64" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Board controls */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-textMuted pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter pipeline..."
            className="w-full bg-surface2 border border-border rounded-md pl-8 pr-3 py-1.5 text-xs focus:outline-none focus:border-accent"
          />
        </div>
        <span className="text-xs text-textMuted">{totalLeads} leads</span>
        <button
          onClick={() => load(true)}
          className="ml-auto p-1.5 hover:bg-surface2 rounded-md text-textMuted hover:text-textPrimary transition-colors"
          title="Refresh"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Kanban columns */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
        {COLUMNS.map((col) => {
          const allLeads = leadsByState[col.state] || [];
          const leads = filterLeads(allLeads);
          return (
            <div
              key={col.state}
              className="bg-surface/30 rounded-xl border border-border flex flex-col"
            >
              {/* Column header */}
              <div className="px-3 py-2.5 border-b border-border flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${col.dot}`} />
                <span className={`text-xs font-semibold ${col.accent}`}>{col.label}</span>
                <span className="ml-auto text-xs font-bold tabular-nums text-textMuted bg-surface2 px-1.5 py-0.5 rounded-full">
                  {search ? `${leads.length}/` : ""}{allLeads.length}
                </span>
              </div>

              {/* Lead cards */}
              <div className="p-2 space-y-2 flex-1 overflow-y-auto max-h-[580px]">
                {leads.length === 0 && (
                  <div className="text-[11px] text-textMuted text-center py-6 opacity-60">
                    {search ? "No match" : "Empty"}
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
    </div>
  );
}
