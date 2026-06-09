"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft, Mail, Phone, Linkedin, Brain, Sparkles,
  MousePointerClick, MessageSquare, Eye, RefreshCw,
} from "lucide-react";
import { api } from "@/lib/api";
import { Lead, AgentDecision } from "@/lib/types";
import { StateBadge } from "@/components/shared/StatusBadge";
import { LeadEnrichmentView } from "@/components/leads/LeadEnrichmentView";
import { LeadStateTimeline } from "@/components/leads/LeadStateTimeline";
import { formatRelative } from "@/lib/utils";

const ENGAGEMENT_SCENARIOS = [
  { id: "opened", label: "Opened Email", icon: Eye, color: "text-blue-300 bg-blue-500/10 border-blue-500/30", description: "Recipient opened the email" },
  { id: "clicked", label: "Clicked Link", icon: MousePointerClick, color: "text-purple-300 bg-purple-500/10 border-purple-500/30", description: "Recipient clicked a link" },
  { id: "replied_interested", label: "Replied: Interested", icon: MessageSquare, color: "text-success bg-success/10 border-success/30", description: '"Would love to learn more"' },
  { id: "replied_positive", label: "Replied: Wants Call", icon: MessageSquare, color: "text-cyan-300 bg-cyan-500/10 border-cyan-500/30", description: '"Can we schedule a call?"' },
  { id: "replied_objection", label: "Replied: Has Competitor", icon: MessageSquare, color: "text-warning bg-warning/10 border-warning/30", description: '"We already use Outreach"' },
];

const EVENT_ICON: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  sent: { icon: Mail, color: "text-blue-300", label: "Email Sent" },
  opened: { icon: Eye, color: "text-purple-300", label: "Opened" },
  clicked: { icon: MousePointerClick, color: "text-cyan-300", label: "Clicked" },
  replied: { icon: MessageSquare, color: "text-success", label: "Replied" },
  delivered: { icon: Mail, color: "text-slate-400", label: "Delivered" },
  bounced: { icon: Mail, color: "text-danger", label: "Bounced" },
};

export default function LeadDetail() {
  const { id } = useParams<{ id: string }>();
  const [lead, setLead] = useState<Lead | null>(null);
  const [decisions, setDecisions] = useState<AgentDecision[]>([]);
  const [emailEvents, setEmailEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [reasoning, setReasoning] = useState(false);
  const [enriching, setEnriching] = useState(false);
  const [simulating, setSimulating] = useState<string | null>(null);
  const [simResult, setSimResult] = useState<string | null>(null);

  const load = async () => {
    try {
      const [l, d] = await Promise.all([
        api.getLead(id),
        api.reasoningHistory(id),
      ]);
      setLead(l);
      setDecisions(d);
      // Email events are embedded in the lead response via relationship
      // We'll fetch them via the decisions + build a synthetic timeline
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [id]);

  const triggerReasoning = async () => {
    setReasoning(true);
    try {
      await api.decideForLead(id);
      await load();
    } catch (e) {
      console.error(e);
      alert("Reasoning failed — check backend logs.");
    } finally {
      setReasoning(false);
    }
  };

  const triggerEnrich = async () => {
    setEnriching(true);
    try {
      await api.enrichLead(id);
      await load();
    } catch (e) {
      console.error(e);
    } finally {
      setEnriching(false);
    }
  };

  const triggerSimulation = async (scenario: string) => {
    setSimulating(scenario);
    setSimResult(null);
    try {
      const result = await api.simulateEngagement(id, scenario);
      setSimResult(result.message);
      await load();
    } catch (e) {
      console.error(e);
    } finally {
      setSimulating(null);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4 max-w-6xl">
        <div className="card animate-pulse h-40" />
        <div className="grid grid-cols-2 gap-4">
          <div className="card animate-pulse h-64" />
          <div className="card animate-pulse h-64" />
        </div>
      </div>
    );
  }
  if (!lead) {
    return <div className="text-danger card p-8 text-center">Lead not found</div>;
  }

  const fullName = `${lead.first_name || ""} ${lead.last_name || ""}`.trim() || lead.email;
  const initials = fullName.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();

  return (
    <div className="space-y-6 max-w-6xl">
      <Link href="/leads" className="text-xs text-textMuted hover:text-accent flex items-center gap-1 w-fit">
        <ArrowLeft className="w-3 h-3" />
        Back to leads
      </Link>

      {/* ── Header card ───────────────────────────────────────────────── */}
      <div className="card">
        <div className="flex items-start gap-4 flex-wrap">
          {/* Avatar */}
          <div className="w-14 h-14 rounded-xl bg-accent/20 text-accent text-xl font-bold flex items-center justify-center shrink-0">
            {initials || "?"}
          </div>

          {/* Name block */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 flex-wrap mb-1">
              <h1 className="text-2xl font-bold">{fullName}</h1>
              <StateBadge state={lead.state} />
              {lead.opted_out && (
                <span className="badge bg-danger/20 text-danger border border-danger/40">Opted Out</span>
              )}
            </div>
            <div className="text-sm text-textMuted">
              {lead.job_title || "Unknown role"}
              {lead.seniority_level && ` · ${lead.seniority_level}`}
              {lead.company?.name && ` @ ${lead.company.name}`}
            </div>
            <div className="flex flex-wrap items-center gap-4 mt-2 text-xs text-textMuted">
              <a href={`mailto:${lead.email}`} className="flex items-center gap-1 hover:text-accent transition-colors">
                <Mail className="w-3 h-3" />
                {lead.email}
              </a>
              {lead.phone && (
                <span className="flex items-center gap-1">
                  <Phone className="w-3 h-3" />
                  {lead.phone}
                </span>
              )}
              {lead.linkedin_url && (
                <a href={lead.linkedin_url} target="_blank" rel="noreferrer" className="flex items-center gap-1 hover:text-accent transition-colors">
                  <Linkedin className="w-3 h-3" />
                  LinkedIn Profile
                </a>
              )}
            </div>
          </div>

          {/* Scores + actions */}
          <div className="flex items-center gap-3 shrink-0 flex-wrap">
            <div className="text-center px-3 py-2 bg-surface2 rounded-lg border border-border">
              <div className="text-xs text-textMuted">Enrichment</div>
              <div className="text-2xl font-bold text-accent">{lead.enrichment_score}</div>
              <div className="text-[10px] text-textMuted">/100</div>
            </div>
            {lead.company && (
              <div className="text-center px-3 py-2 bg-surface2 rounded-lg border border-border">
                <div className="text-xs text-textMuted">ICP Fit</div>
                <div className="text-2xl font-bold text-success">{lead.company.icp_fit_score}</div>
                <div className="text-[10px] text-textMuted">/100</div>
              </div>
            )}
            <div className="flex flex-col gap-2">
              <button
                onClick={triggerReasoning}
                disabled={reasoning}
                className="btn-primary flex items-center gap-2 disabled:opacity-50"
              >
                <Brain className="w-4 h-4" />
                {reasoning ? "Reasoning..." : "Run Agent"}
              </button>
              <button
                onClick={triggerEnrich}
                disabled={enriching}
                className="btn-ghost flex items-center gap-2 disabled:opacity-50 text-xs"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${enriching ? "animate-spin" : ""}`} />
                {enriching ? "Enriching..." : "Re-enrich"}
              </button>
            </div>
          </div>
        </div>

        {lead.next_action_at && (
          <div className="mt-4 pt-4 border-t border-border flex items-center gap-2 text-xs text-textMuted">
            <Brain className="w-3 h-3" />
            Next scheduled action: {formatRelative(lead.next_action_at)}
          </div>
        )}
      </div>

      {/* ── Buyer-side engagement simulator ──────────────────────────── */}
      <div className="card">
        <div className="flex items-center gap-2 mb-1">
          <Eye className="w-4 h-4 text-accent" />
          <h2 className="font-semibold text-sm">Simulate Buyer Engagement</h2>
          <span className="ml-2 badge bg-warning/10 border border-warning/30 text-warning text-[10px]">Demo tool</span>
        </div>
        <p className="text-xs text-textMuted mb-4">
          Simulate what happens on the buyer's side. In production, SendGrid webhooks fire these automatically
          when a recipient opens, clicks, or replies. Here you can trigger them manually to show the agent reacting.
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
          {ENGAGEMENT_SCENARIOS.map((s) => {
            const Icon = s.icon;
            return (
              <button
                key={s.id}
                onClick={() => triggerSimulation(s.id)}
                disabled={simulating !== null}
                className={`flex flex-col items-center gap-1.5 p-3 rounded-lg border text-center transition-all disabled:opacity-50 hover:opacity-90 ${s.color}`}
              >
                {simulating === s.id
                  ? <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  : <Icon className="w-5 h-5" />}
                <span className="text-xs font-semibold leading-tight">{s.label}</span>
                <span className="text-[10px] opacity-70 leading-tight">{s.description}</span>
              </button>
            );
          })}
        </div>

        {simResult && (
          <div className="mt-3 p-3 bg-success/10 border border-success/30 rounded-lg text-xs text-success">
            ✓ {simResult}
          </div>
        )}
      </div>

      {/* ── Main grid ────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_380px] gap-6">
        <div className="space-y-6">
          {/* Enrichment */}
          <section>
            <h2 className="text-xs font-semibold uppercase tracking-wide text-textMuted mb-3 flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5" />
              Lead Enrichment
            </h2>
            <LeadEnrichmentView lead={lead} />
          </section>
        </div>

        {/* Agent chain of thought */}
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-wide text-textMuted mb-3 flex items-center gap-2">
            <Brain className="w-3.5 h-3.5" />
            Agent Reasoning History
            <span className="ml-auto text-[10px] text-textMuted font-normal">{decisions.length} decisions</span>
          </h2>
          <LeadStateTimeline decisions={decisions} />
        </div>
      </div>
    </div>
  );
}
