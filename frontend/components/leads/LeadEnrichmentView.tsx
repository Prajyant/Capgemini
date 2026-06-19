"use client";

import { Lead } from "@/lib/types";
import {
  Building2,
  Cpu,
  HelpCircle,
  Linkedin,
  Newspaper,
  Trash2,
  TrendingUp,
} from "lucide-react";
import { useState } from "react";
import { api } from "@/lib/api";
import { NewsInjector } from "./NewsInjector";

export function LeadEnrichmentView({
  lead,
  onChanged,
}: {
  lead: Lead;
  onChanged?: () => void;
}) {
  const company = lead.company;
  const news = lead.company_news || company?.recent_news || [];
  const tech = lead.tech_stack || company?.tech_stack || [];
  const intent: any = lead.intent_signals || {};
  const linkedin: any = lead.linkedin_signals || {};

  const [removingIdx, setRemovingIdx] = useState<number | null>(null);

  async function removeNews(idx: number) {
    setRemovingIdx(idx);
    try {
      await api.removeLeadNews(lead.id, idx);
      onChanged?.();
    } catch (e) {
      console.error(e);
    } finally {
      setRemovingIdx(null);
    }
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Company */}
      <div className="card">
        <div className="flex items-center gap-2 mb-3">
          <Building2 className="w-4 h-4 text-accent" />
          <h3 className="font-semibold text-sm">Company</h3>
        </div>
        <div className="space-y-1.5 text-sm">
          <div className="flex justify-between gap-3">
            <span className="text-textMuted">Name</span>
            <span className="text-right">{company?.name || "—"}</span>
          </div>
          <div className="flex justify-between gap-3">
            <span className="text-textMuted">Domain</span>
            <span className="text-right">{company?.domain || "—"}</span>
          </div>
          <div className="flex justify-between gap-3">
            <span className="text-textMuted">Industry</span>
            <span className="text-right">{company?.industry || "—"}</span>
          </div>
          <div className="flex justify-between gap-3">
            <span className="text-textMuted">Size</span>
            <span className="text-right">{company?.employee_range || company?.employee_count || "—"}</span>
          </div>
          <div className="flex justify-between gap-3">
            <span className="text-textMuted">Funding</span>
            <span className="text-right">{company?.funding_stage || "—"}</span>
          </div>
          <div className="flex justify-between gap-3 items-center">
            <span className="text-textMuted flex items-center gap-1">
              ICP Fit Score
              <ScoreInfo
                title="ICP Fit Score"
                lines={[
                  "Baseline 50",
                  "+20 if 50–500 employees",
                  "+15 if SaaS / software / tech",
                  "+10 if Series A/B/C",
                  "+5 if VP / C-Level / Director / Founder",
                  "Capped at 100",
                ]}
              />
            </span>
            <span className="text-right font-bold text-accent">{company?.icp_fit_score ?? "—"}/100</span>
          </div>
          <div className="flex justify-between gap-3 items-center">
            <span className="text-textMuted flex items-center gap-1">
              Enrichment Score
              <ScoreInfo
                title="Enrichment Score"
                lines={[
                  "How much we know about this lead.",
                  "+20 if LinkedIn signals present",
                  "+8 per news item (cap 30)",
                  "+2 per tech item (cap 30)",
                  "+20 if any buying intent fires",
                  "Capped at 100",
                ]}
              />
            </span>
            <span className="text-right font-bold text-accent">
              {lead.enrichment_score ?? 0}/100
            </span>
          </div>
        </div>
      </div>

      {/* Intent */}
      <div className="card">
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp className="w-4 h-4 text-success" />
          <h3 className="font-semibold text-sm">Buying Intent</h3>
          <ScoreInfo
            title="Buying Intent Score"
            lines={[
              "Funding/IPO news: up to 30 (recency-weighted)",
              "Hiring activity: up to 25 (5 + 5 per match)",
              "Tech replacement: up to 30 (10 per competitor tool)",
              "Senior decision-maker: +10",
              "Buyer engagement: up to 35 (replies > clicks > opens)",
              "Capped at 100",
            ]}
          />
        </div>
        <div className="space-y-2">
          <div className="flex items-baseline justify-between">
            <span className="text-textMuted text-sm">Intent Score</span>
            <span className="text-2xl font-bold text-success">
              {intent.intent_score ?? company?.intent_score ?? 0}
            </span>
          </div>
          <div className="flex flex-wrap gap-1">
            {intent.funding_recent && (
              <span className="badge bg-success/15 text-success border border-success/30">
                Recent funding
              </span>
            )}
            {intent.hiring_count > 0 && (
              <span className="badge bg-warning/15 text-warning border border-warning/30">
                Hiring · {intent.hiring_count} signal{intent.hiring_count === 1 ? "" : "s"}
              </span>
            )}
            {(intent.engagement_signals || []).map((s: string) => (
              <span
                key={s}
                className="badge bg-accent/15 text-accent border border-accent/30 capitalize"
              >
                {s.replace(/_/g, " ")}
              </span>
            ))}
          </div>
          {intent.tech_replacement_signals?.length > 0 && (
            <div className="text-xs text-textMuted">
              Replaceable tech: {intent.tech_replacement_signals.join(", ")}
            </div>
          )}
          {(intent.reasons || []).length > 0 && (
            <ul className="mt-2 space-y-1 text-xs text-textMuted list-disc list-inside">
              {intent.reasons.map((r: string, i: number) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          )}
          {(!intent.reasons || intent.reasons.length === 0) && (
            <div className="text-xs text-textMuted italic">
              No intent signals detected yet.
            </div>
          )}
        </div>
      </div>

      {/* News */}
      <div className="card">
        <div className="flex items-center justify-between mb-3 gap-2">
          <div className="flex items-center gap-2">
            <Newspaper className="w-4 h-4 text-cyan-300" />
            <h3 className="font-semibold text-sm">Recent News</h3>
          </div>
          {onChanged && (
            <NewsInjector
              leadId={lead.id}
              companyName={company?.name}
              onChanged={onChanged}
            />
          )}
        </div>
        <div className="space-y-2">
          {news.length === 0 && (
            <div className="text-xs text-textMuted">No recent news</div>
          )}
          {news.slice(0, 5).map((n, i) => (
            <div key={i} className="flex items-start justify-between gap-2 group">
              <a
                href={n.url || "#"}
                target={n.url ? "_blank" : undefined}
                rel="noopener noreferrer"
                className="block text-xs hover:text-accent flex-1 min-w-0"
                onClick={(e) => {
                  if (!n.url) e.preventDefault();
                }}
              >
                <div className="font-medium leading-snug">{n.headline}</div>
                <div className="text-textMuted text-[10px] mt-0.5">
                  {n.source} · {n.published_at}
                </div>
              </a>
              {onChanged && (
                <button
                  onClick={() => removeNews(i)}
                  disabled={removingIdx === i}
                  className="opacity-0 group-hover:opacity-100 text-textMuted hover:text-danger transition shrink-0 p-1 disabled:opacity-30"
                  title="Remove this news item"
                  aria-label="Remove news item"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Tech Stack */}
      <div className="card">
        <div className="flex items-center gap-2 mb-3">
          <Cpu className="w-4 h-4 text-purple-300" />
          <h3 className="font-semibold text-sm">Tech Stack</h3>
        </div>
        <div className="flex flex-wrap gap-1">
          {tech.length === 0 && (
            <div className="text-xs text-textMuted">No data</div>
          )}
          {tech.map((t, i) => (
            <span
              key={i}
              className="badge bg-surface2 border border-border text-textPrimary"
            >
              {t}
            </span>
          ))}
        </div>
      </div>

      {/* LinkedIn */}
      <div className="card md:col-span-2">
        <div className="flex items-center gap-2 mb-3">
          <Linkedin className="w-4 h-4 text-blue-300" />
          <h3 className="font-semibold text-sm">LinkedIn Signals</h3>
        </div>
        {Object.keys(linkedin).length === 0 ? (
          <div className="text-xs text-textMuted">No LinkedIn data available</div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            {linkedin.tenure_months && (
              <div>
                <div className="text-xs text-textMuted">Tenure</div>
                <div className="font-medium">{linkedin.tenure_months} months</div>
              </div>
            )}
            {linkedin.post_frequency && (
              <div>
                <div className="text-xs text-textMuted">Post Frequency</div>
                <div className="font-medium capitalize">{linkedin.post_frequency}</div>
              </div>
            )}
            {linkedin.connections_count && (
              <div>
                <div className="text-xs text-textMuted">Connections</div>
                <div className="font-medium">{linkedin.connections_count}</div>
              </div>
            )}
            {linkedin.is_active !== undefined && (
              <div>
                <div className="text-xs text-textMuted">Active</div>
                <div className="font-medium">{linkedin.is_active ? "Yes" : "No"}</div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Tiny inline tooltip explaining how a score is computed. Hover the icon
 * to see the bullet list — handy for showing judges the formula without
 * dragging them through the codebase.
 */
function ScoreInfo({ title, lines }: { title: string; lines: string[] }) {
  return (
    <span className="relative inline-flex group">
      <HelpCircle className="w-3.5 h-3.5 text-textMuted/70 hover:text-accent cursor-help" />
      <span className="absolute left-1/2 -translate-x-1/2 top-full mt-1 w-64 hidden group-hover:block bg-surface border border-border rounded-md shadow-xl p-2.5 z-20 text-left">
        <span className="block text-xs font-semibold text-textPrimary mb-1">
          {title}
        </span>
        <ul className="text-[11px] text-textMuted space-y-0.5">
          {lines.map((l, i) => (
            <li key={i}>{l}</li>
          ))}
        </ul>
      </span>
    </span>
  );
}
