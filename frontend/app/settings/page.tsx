"use client";

import { useEffect, useState } from "react";
import { Key, Database, Mail, Shield, Check, X, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

type Status = {
  llm: { provider: string; key_configured: boolean; available_providers: string[] };
  integrations: Record<string, boolean>;
  agent: { autopilot_mode: boolean; confidence_threshold: number };
  sender: {
    from_email: string;
    from_name: string;
    physical_address: string;
  };
  environment: string;
};

export default function SettingsPage() {
  const [status, setStatus] = useState<Status | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .settingsStatus()
      .then((s) => setStatus(s))
      .catch((e) => setError(e?.message || "Failed to load settings"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="card flex items-center gap-2 text-textMuted">
        <Loader2 className="w-4 h-4 animate-spin" /> Loading settings...
      </div>
    );
  }

  if (error || !status) {
    return (
      <div className="card text-danger flex items-center gap-2">
        <X className="w-4 h-4" /> {error || "No settings available"}
      </div>
    );
  }

  const llmItems = [
    { name: "Groq", key: "groq" },
    { name: "Google Gemini", key: "gemini" },
    { name: "OpenAI", key: "openai" },
    { name: "Anthropic Claude", key: "anthropic" },
  ];

  const enrichmentItems = [
    { name: "SendGrid", key: "sendgrid", note: "real email send" },
    { name: "NewsAPI", key: "newsapi", note: "optional — Google News RSS works without it" },
    { name: "BuiltWith", key: "builtwith", note: "tech stack lookup" },
    { name: "LinkedIn", key: "linkedin", note: "synthetic signals if absent" },
  ];

  const crmItems = [
    { name: "HubSpot", key: "hubspot" },
    { name: "Salesforce", key: "salesforce" },
  ];

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold mb-1">Settings</h1>
          <p className="text-sm text-textMuted">
            Live snapshot of your environment. Values come from the backend, not
            from the UI — change them in your <code>.env</code> and restart.
          </p>
        </div>
        <span className="badge bg-surface2 border border-border capitalize">
          {status.environment}
        </span>
      </div>

      {/* LLM */}
      <Section
        icon={Key}
        title="AI Provider"
        description="The LLM the agent reasons with. Switch via LLM_PROVIDER in .env."
      >
        <Row
          label="Active provider"
          value={
            <span className="capitalize font-medium">{status.llm.provider}</span>
          }
        />
        <Row
          label={`${capitalize(status.llm.provider)} key`}
          value={<StatusPill ok={status.llm.key_configured} />}
        />
        <div className="pt-2 mt-2 border-t border-border/30 space-y-2">
          <div className="text-xs text-textMuted">All known providers</div>
          {llmItems.map((p) => (
            <Row
              key={p.key}
              label={p.name}
              value={<StatusPill ok={!!status.integrations[p.key]} />}
            />
          ))}
        </div>
      </Section>

      {/* Email + Enrichment */}
      <Section
        icon={Mail}
        title="Email & Enrichment"
        description="External providers used by outreach and enrichment."
      >
        {enrichmentItems.map((p) => (
          <Row
            key={p.key}
            label={
              <span>
                {p.name}{" "}
                <span className="text-textMuted text-xs">— {p.note}</span>
              </span>
            }
            value={<StatusPill ok={!!status.integrations[p.key]} />}
          />
        ))}
      </Section>

      {/* CRM */}
      <Section
        icon={Database}
        title="CRM Connections"
        description="OAuth-based CRM sync. Set the client ID/secret pair in .env to enable."
      >
        {crmItems.map((p) => (
          <Row
            key={p.key}
            label={p.name}
            value={
              status.integrations[p.key] ? (
                <StatusPill ok />
              ) : (
                <span className="badge bg-surface2 border border-border text-textMuted">
                  Coming soon
                </span>
              )
            }
          />
        ))}
      </Section>

      {/* Agent behaviour */}
      <Section
        icon={Shield}
        title="Agent Behaviour"
        description="How the agent acts. Tune via AUTOPILOT_MODE and CONFIDENCE_THRESHOLD."
      >
        <Row
          label="Autopilot mode"
          value={
            <span
              className={`badge ${
                status.agent.autopilot_mode
                  ? "bg-success/15 text-success border border-success/30"
                  : "bg-surface2 border border-border text-textMuted"
              }`}
            >
              {status.agent.autopilot_mode ? "On" : "Off"}
            </span>
          }
        />
        <Row
          label="Confidence threshold"
          value={
            <span className="font-medium">
              {Math.round(status.agent.confidence_threshold * 100)}%
            </span>
          }
        />
      </Section>

      {/* Sender */}
      <Section
        icon={Mail}
        title="Sender Identity"
        description="Used in the From header and CAN-SPAM footer."
      >
        <Row label="From name" value={status.sender.from_name} />
        <Row label="From email" value={status.sender.from_email} />
        <Row label="Physical address" value={status.sender.physical_address} />
      </Section>
    </div>
  );
}

function capitalize(s: string) {
  return s ? s[0].toUpperCase() + s.slice(1) : s;
}

function Section({
  icon: Icon,
  title,
  description,
  children,
}: {
  icon: any;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="card">
      <div className="flex items-start gap-3 mb-3">
        <div className="p-2 bg-accent/15 rounded-md text-accent">
          <Icon className="w-4 h-4" />
        </div>
        <div>
          <div className="font-semibold">{title}</div>
          <div className="text-xs text-textMuted">{description}</div>
        </div>
      </div>
      <div className="space-y-2 ml-12">{children}</div>
    </div>
  );
}

function Row({
  label,
  value,
}: {
  label: React.ReactNode;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between text-sm border-b border-border/30 pb-2 last:border-0">
      <span>{label}</span>
      <span>{value}</span>
    </div>
  );
}

function StatusPill({ ok }: { ok: boolean }) {
  return ok ? (
    <span className="badge bg-success/15 text-success border border-success/30 flex items-center gap-1">
      <Check className="w-3 h-3" /> Configured
    </span>
  ) : (
    <span className="badge bg-surface2 border border-border text-textMuted flex items-center gap-1">
      <X className="w-3 h-3" /> Not set
    </span>
  );
}
