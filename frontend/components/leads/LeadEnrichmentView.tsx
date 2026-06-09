"use client";

import { Lead } from "@/lib/types";
import { Newspaper, Cpu, TrendingUp, Linkedin, Building2, ExternalLink, AlertTriangle, CheckCircle } from "lucide-react";

export function LeadEnrichmentView({ lead }: { lead: Lead }) {
  const company = lead.company;
  const news = lead.company_news || company?.recent_news || [];
  const tech = lead.tech_stack || company?.tech_stack || [];
  const intent = lead.intent_signals || {};
  const linkedin = lead.linkedin_signals || {};
  const intentScore = intent.intent_score ?? company?.intent_score ?? 0;

  const intentColor =
    intentScore >= 60 ? "text-success" :
    intentScore >= 30 ? "text-warning" :
    "text-textMuted";

  const intentBg =
    intentScore >= 60 ? "bg-success/15 border-success/30" :
    intentScore >= 30 ? "bg-warning/15 border-warning/30" :
    "bg-surface2 border-border";

  // Group tech by competitor vs normal
  const COMPETITOR_TECH = new Set(["Outreach", "SalesLoft", "Apollo", "Lemlist", "Mixmax", "Reply.io"]);
  const competitorTech = tech.filter((t) => COMPETITOR_TECH.has(t));
  const normalTech = tech.filter((t) => !COMPETITOR_TECH.has(t));

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Company */}
      <div className="card">
        <div className="flex items-center gap-2 mb-3">
          <Building2 className="w-4 h-4 text-accent" />
          <h3 className="font-semibold text-sm">Company Profile</h3>
        </div>
        <div className="space-y-2">
          {[
            ["Name", company?.name],
            ["Domain", company?.domain ? (
              <a href={`https://${company.domain}`} target="_blank" rel="noreferrer" className="hover:text-accent flex items-center gap-1">
                {company.domain} <ExternalLink className="w-3 h-3" />
              </a>
            ) : null],
            ["Industry", company?.industry],
            ["Team Size", company?.employee_range || (company?.employee_count ? `~${company.employee_count}` : null)],
            ["Funding Stage", company?.funding_stage],
            ["Location", company?.location],
          ].map(([label, value]) => (
            <div key={String(label)} className="flex items-start justify-between gap-3 text-sm py-1 border-b border-border/30 last:border-0">
              <span className="text-textMuted shrink-0">{label}</span>
              <span className="text-right text-textPrimary font-medium">{value || "—"}</span>
            </div>
          ))}
          <div className="flex items-center justify-between text-sm pt-1">
            <span className="text-textMuted">ICP Fit Score</span>
            <div className="flex items-center gap-2">
              <div className="w-20 h-1.5 bg-surface2 rounded-full overflow-hidden">
                <div className="h-full bg-accent rounded-full" style={{ width: `${company?.icp_fit_score ?? 0}%` }} />
              </div>
              <span className="font-bold text-accent tabular-nums">{company?.icp_fit_score ?? 0}/100</span>
            </div>
          </div>
        </div>
      </div>

      {/* Buying Intent */}
      <div className="card">
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp className="w-4 h-4 text-success" />
          <h3 className="font-semibold text-sm">Buying Intent Signals</h3>
        </div>

        {/* Score */}
        <div className={`rounded-lg p-3 border mb-3 ${intentBg}`}>
          <div className="flex items-baseline justify-between">
            <span className="text-sm text-textMuted">Intent Score</span>
            <span className={`text-3xl font-bold tabular-nums ${intentColor}`}>{intentScore}</span>
          </div>
          <div className="w-full h-1.5 bg-black/20 rounded-full mt-2 overflow-hidden">
            <div className={`h-full rounded-full ${intentScore >= 60 ? "bg-success" : intentScore >= 30 ? "bg-warning" : "bg-textMuted"}`}
              style={{ width: `${intentScore}%` }} />
          </div>
        </div>

        {/* Signal breakdown */}
        <div className="space-y-1.5">
          <SignalRow
            active={!!intent.funding_recent}
            label={intent.funding_details || "Recent funding round"}
            type="funding"
          />
          <SignalRow
            active={intent.hiring_sales_team || intent.hiring_count > 0}
            label={`Hiring${intent.hiring_count > 0 ? ` (${intent.hiring_count}+ roles)` : ""}`}
            type="hiring"
          />
          <SignalRow
            active={!!intent.growth_signal}
            label={intent.growth_details || "Company growth signal"}
            type="growth"
          />
          <SignalRow
            active={competitorTech.length > 0}
            label={competitorTech.length > 0 ? `Using ${competitorTech.join(", ")}` : "No competitor tools"}
            type="competitor"
          />
        </div>
      </div>

      {/* News */}
      <div className="card">
        <div className="flex items-center gap-2 mb-3">
          <Newspaper className="w-4 h-4 text-cyan-300" />
          <h3 className="font-semibold text-sm">Recent News</h3>
          <span className="ml-auto text-[10px] text-textMuted">{news.length} article{news.length !== 1 ? "s" : ""}</span>
        </div>
        <div className="space-y-3">
          {news.length === 0 && (
            <div className="text-xs text-textMuted py-2">
              No recent news found. News enriches automatically when a company domain is provided.
            </div>
          )}
          {news.slice(0, 4).map((n, i) => (
            <div key={i} className="border-b border-border/30 pb-2 last:border-0">
              {n.url ? (
                <a
                  href={n.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs font-medium leading-snug hover:text-accent flex items-start gap-1 group"
                >
                  <span className="flex-1">{n.headline}</span>
                  <ExternalLink className="w-3 h-3 shrink-0 mt-0.5 opacity-0 group-hover:opacity-100 transition" />
                </a>
              ) : (
                <div className="text-xs font-medium leading-snug">{n.headline}</div>
              )}
              <div className="text-[10px] text-textMuted mt-0.5 flex items-center gap-1.5">
                {n.source && <span>{n.source}</span>}
                {n.published_at && <span>· {new Date(n.published_at).toLocaleDateString()}</span>}
              </div>
              {n.summary && (
                <div className="text-[10px] text-textMuted mt-0.5 line-clamp-2">{n.summary}</div>
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
          <span className="ml-auto text-[10px] text-textMuted">{tech.length} tools detected</span>
        </div>
        {tech.length === 0 ? (
          <div className="text-xs text-textMuted">
            No tech data. Provide a company domain to enable tech stack detection.
          </div>
        ) : (
          <div className="space-y-3">
            {competitorTech.length > 0 && (
              <div>
                <div className="text-[10px] uppercase tracking-wide text-warning mb-1.5">
                  Competitor / Replaceable Tools
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {competitorTech.map((t, i) => (
                    <span key={i} className="badge bg-warning/15 border border-warning/30 text-warning">
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            )}
            <div>
              {competitorTech.length > 0 && (
                <div className="text-[10px] uppercase tracking-wide text-textMuted mb-1.5">Other Tools</div>
              )}
              <div className="flex flex-wrap gap-1.5">
                {normalTech.map((t, i) => (
                  <span key={i} className="badge bg-surface2 border border-border text-textPrimary">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* LinkedIn */}
      <div className="card md:col-span-2">
        <div className="flex items-center gap-2 mb-3">
          <Linkedin className="w-4 h-4 text-blue-300" />
          <h3 className="font-semibold text-sm">LinkedIn Signals</h3>
          {linkedin.source === "synthetic" && (
            <span className="ml-auto text-[10px] badge bg-warning/10 border border-warning/30 text-warning">
              Demo data — real integration requires Proxycurl/Apollo API
            </span>
          )}
        </div>
        {Object.keys(linkedin).length === 0 ? (
          <div className="text-xs text-textMuted">
            No LinkedIn data. Add a LinkedIn URL to the lead to enable signal detection.
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            {linkedin.tenure_months != null && (
              <div className="card bg-surface2/50">
                <div className="text-[10px] text-textMuted uppercase tracking-wide mb-1">Tenure</div>
                <div className="font-bold text-lg">{linkedin.tenure_months}<span className="text-xs font-normal text-textMuted"> mo</span></div>
              </div>
            )}
            {linkedin.post_frequency && (
              <div className="card bg-surface2/50">
                <div className="text-[10px] text-textMuted uppercase tracking-wide mb-1">Posts</div>
                <div className="font-bold text-lg capitalize">{linkedin.post_frequency}</div>
              </div>
            )}
            {linkedin.connections_count && (
              <div className="card bg-surface2/50">
                <div className="text-[10px] text-textMuted uppercase tracking-wide mb-1">Network</div>
                <div className="font-bold text-lg">{linkedin.connections_count}</div>
              </div>
            )}
            {linkedin.is_active != null && (
              <div className="card bg-surface2/50">
                <div className="text-[10px] text-textMuted uppercase tracking-wide mb-1">Active</div>
                <div className={`font-bold text-lg ${linkedin.is_active ? "text-success" : "text-textMuted"}`}>
                  {linkedin.is_active ? "Yes" : "No"}
                </div>
              </div>
            )}
            {linkedin.recent_post_topics?.length > 0 && (
              <div className="col-span-2 sm:col-span-4 mt-1">
                <div className="text-[10px] text-textMuted uppercase tracking-wide mb-1.5">Recent Post Topics</div>
                <div className="flex flex-wrap gap-1.5">
                  {linkedin.recent_post_topics.map((t: string, i: number) => (
                    <span key={i} className="badge bg-blue-500/10 border border-blue-500/30 text-blue-300 text-xs">
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function SignalRow({ active, label, type }: { active: boolean; label: string; type: string }) {
  const colors: Record<string, string> = {
    funding: "text-success",
    hiring: "text-warning",
    growth: "text-cyan-300",
    competitor: "text-purple-300",
  };
  return (
    <div className={`flex items-center gap-2 text-xs py-1 ${active ? colors[type] || "text-textPrimary" : "text-textMuted/50"}`}>
      {active
        ? <CheckCircle className="w-3.5 h-3.5 shrink-0" />
        : <AlertTriangle className="w-3.5 h-3.5 shrink-0 opacity-30" />}
      <span className={active ? "font-medium" : "line-through opacity-40"}>{label}</span>
    </div>
  );
}
