"use client";

import { Lead } from "@/lib/types";
import { Newspaper, Cpu, TrendingUp, Linkedin, Building2 } from "lucide-react";

export function LeadEnrichmentView({ lead }: { lead: Lead }) {
  const company = lead.company;
  const news = lead.company_news || company?.recent_news || [];
  const tech = lead.tech_stack || company?.tech_stack || [];
  const intent = lead.intent_signals || {};
  const linkedin = lead.linkedin_signals || {};

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
          <div className="flex justify-between gap-3">
            <span className="text-textMuted">ICP Fit Score</span>
            <span className="text-right font-bold text-accent">{company?.icp_fit_score ?? "—"}/100</span>
          </div>
        </div>
      </div>

      {/* Intent */}
      <div className="card">
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp className="w-4 h-4 text-success" />
          <h3 className="font-semibold text-sm">Buying Intent</h3>
        </div>
        <div className="space-y-2">
          <div className="flex items-baseline justify-between">
            <span className="text-textMuted text-sm">Intent Score</span>
            <span className="text-2xl font-bold text-success">{intent.intent_score ?? company?.intent_score ?? 0}</span>
          </div>
          {intent.funding_recent && (
            <div className="badge bg-success/15 text-success border border-success/30">
              Recent funding
            </div>
          )}
          {intent.hiring_count > 0 && (
            <div className="badge bg-warning/15 text-warning border border-warning/30 ml-1">
              Hiring · {intent.hiring_count} roles
            </div>
          )}
          {intent.tech_replacement_signals?.length > 0 && (
            <div className="mt-2 text-xs text-textMuted">
              Replaceable tech: {intent.tech_replacement_signals.join(", ")}
            </div>
          )}
        </div>
      </div>

      {/* News */}
      <div className="card">
        <div className="flex items-center gap-2 mb-3">
          <Newspaper className="w-4 h-4 text-cyan-300" />
          <h3 className="font-semibold text-sm">Recent News</h3>
        </div>
        <div className="space-y-2">
          {news.length === 0 && (
            <div className="text-xs text-textMuted">No recent news</div>
          )}
          {news.slice(0, 3).map((n, i) => (
            <a
              key={i}
              href={n.url || "#"}
              target="_blank"
              rel="noopener noreferrer"
              className="block text-xs hover:text-accent"
            >
              <div className="font-medium leading-snug">{n.headline}</div>
              <div className="text-textMuted text-[10px] mt-0.5">
                {n.source} · {n.published_at}
              </div>
            </a>
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
