"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Mail, Phone, Linkedin, Brain, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { Lead, AgentDecision } from "@/lib/types";
import { StateBadge } from "@/components/shared/StatusBadge";
import { LeadEnrichmentView } from "@/components/leads/LeadEnrichmentView";
import { LeadStateTimeline } from "@/components/leads/LeadStateTimeline";
import {
  LeadEngagementPanel,
  EngagementEvent,
} from "@/components/leads/LeadEngagementPanel";
import { formatRelative } from "@/lib/utils";

export default function LeadDetail() {
  const { id } = useParams<{ id: string }>();
  const [lead, setLead] = useState<Lead | null>(null);
  const [decisions, setDecisions] = useState<AgentDecision[]>([]);
  const [events, setEvents] = useState<EngagementEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [reasoning, setReasoning] = useState(false);

  const load = async () => {
    try {
      const [l, d, ev] = await Promise.all([
        api.getLead(id),
        api.reasoningHistory(id),
        api.getLeadEvents(id).catch(() => []),
      ]);
      setLead(l);
      setDecisions(d);
      setEvents(ev || []);
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
      alert("Reasoning failed. Check backend logs.");
    } finally {
      setReasoning(false);
    }
  };

  if (loading) {
    return <div className="text-textMuted">Loading lead...</div>;
  }
  if (!lead) {
    return <div className="text-danger">Lead not found</div>;
  }

  const fullName =
    `${lead.first_name || ""} ${lead.last_name || ""}`.trim() || lead.email;

  return (
    <div className="space-y-6 max-w-6xl">
      <Link
        href="/leads"
        className="text-xs text-textMuted hover:text-accent flex items-center gap-1"
      >
        <ArrowLeft className="w-3 h-3" />
        Back to leads
      </Link>

      {/* Header */}
      <div className="card">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-2xl font-bold">{fullName}</h1>
              <StateBadge state={lead.state} />
            </div>
            <div className="text-sm text-textMuted">
              {lead.job_title} · {lead.company?.name || "—"}
            </div>
            <div className="flex items-center gap-3 mt-3 text-xs text-textMuted">
              <a
                href={`mailto:${lead.email}`}
                className="flex items-center gap-1 hover:text-accent"
              >
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
                <a
                  href={lead.linkedin_url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1 hover:text-accent"
                >
                  <Linkedin className="w-3 h-3" />
                  LinkedIn
                </a>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="text-right mr-2">
              <div className="text-xs text-textMuted">Enrichment</div>
              <div className="text-2xl font-bold text-accent">
                {lead.enrichment_score}
              </div>
            </div>
            <button
              onClick={triggerReasoning}
              disabled={reasoning}
              className="btn-primary flex items-center gap-2 disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4" />
              {reasoning ? "Reasoning..." : "Run Agent Reasoning"}
            </button>
          </div>
        </div>

        {lead.next_action_at && (
          <div className="mt-4 pt-4 border-t border-border text-xs text-textMuted">
            Next scheduled action: {formatRelative(lead.next_action_at)}
          </div>
        )}
      </div>

      {/* Enrichment Section */}
      <section>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-textMuted mb-3">
          Lead Profile & Enrichment
        </h2>
        <LeadEnrichmentView lead={lead} />
      </section>

      {/* Prior Engagement (buyer-side mailbox) */}
      <section className="relative">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-textMuted mb-3">
          Prior Engagement
        </h2>
        <LeadEngagementPanel
          events={events}
          leadEmail={lead.email}
          onSimulated={load}
        />
      </section>

      {/* Reasoning Timeline */}
      <section>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-textMuted mb-3 flex items-center gap-2">
          <Brain className="w-4 h-4" />
          Agent Chain of Thought
        </h2>
        <LeadStateTimeline decisions={decisions} />
      </section>
    </div>
  );
}
