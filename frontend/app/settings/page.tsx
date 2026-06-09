"use client";

import { useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { Key, Database, Mail, Shield, CheckCircle, XCircle, Loader2, Link, Unlink } from "lucide-react";
import { api, BACKEND_URL } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

interface CrmStatus {
  connected: boolean;
  status: string;
}

interface CrmStatuses {
  hubspot: CrmStatus;
  salesforce: CrmStatus;
}

// ── CRM Connection Row ─────────────────────────────────────────────────────

function CrmRow({
  name,
  crmKey,
  status,
  onConnect,
  onDisconnect,
  loading,
}: {
  name: string;
  crmKey: "hubspot" | "salesforce";
  status: CrmStatus | null;
  onConnect: (crm: "hubspot" | "salesforce") => void;
  onDisconnect: (crm: "hubspot" | "salesforce") => void;
  loading: boolean;
}) {
  const connected = status?.connected ?? false;

  return (
    <div className="flex items-center justify-between text-sm border-b border-border/30 pb-2 last:border-0">
      <div className="flex items-center gap-2">
        {connected ? (
          <CheckCircle className="w-3.5 h-3.5 text-green-400" />
        ) : (
          <XCircle className="w-3.5 h-3.5 text-textMuted" />
        )}
        <span>{name}</span>
      </div>

      <div className="flex items-center gap-2">
        <span className={`text-xs ${connected ? "text-green-400" : "text-textMuted"}`}>
          {status ? status.status : "checking…"}
        </span>

        {loading ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin text-textMuted" />
        ) : connected ? (
          <button
            onClick={() => onDisconnect(crmKey)}
            className="flex items-center gap-1 text-xs px-2 py-1 rounded bg-red-500/15 text-red-400 hover:bg-red-500/25 transition-colors"
          >
            <Unlink className="w-3 h-3" />
            Disconnect
          </button>
        ) : (
          <button
            onClick={() => onConnect(crmKey)}
            className="flex items-center gap-1 text-xs px-2 py-1 rounded bg-accent/15 text-accent hover:bg-accent/25 transition-colors"
          >
            <Link className="w-3 h-3" />
            Connect
          </button>
        )}
      </div>
    </div>
  );
}

// ── Toast ──────────────────────────────────────────────────────────────────

function Toast({ message, type }: { message: string; type: "success" | "error" }) {
  return (
    <div
      className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg text-sm font-medium transition-all
        ${type === "success" ? "bg-green-500/20 border border-green-500/40 text-green-300" : "bg-red-500/20 border border-red-500/40 text-red-300"}`}
    >
      {type === "success" ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
      {message}
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const searchParams = useSearchParams();

  const [crmStatus, setCrmStatus] = useState<CrmStatuses | null>(null);
  const [crmLoading, setCrmLoading] = useState<"hubspot" | "salesforce" | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const showToast = (message: string, type: "success" | "error") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const fetchCrmStatus = useCallback(async () => {
    try {
      const data = await api.crmStatus();
      setCrmStatus(data);
    } catch {
      // Redis or backend may not be up — show defaults
      setCrmStatus({
        hubspot: { connected: false, status: "not connected" },
        salesforce: { connected: false, status: "not connected" },
      });
    }
  }, []);

  // On mount: fetch status + handle OAuth redirect result
  useEffect(() => {
    fetchCrmStatus();

    const crm = searchParams.get("crm") as "hubspot" | "salesforce" | null;
    const status = searchParams.get("status");
    const error = searchParams.get("error");

    if (crm && status === "connected") {
      showToast(`${crm === "hubspot" ? "HubSpot" : "Salesforce"} connected successfully`, "success");
      // Refresh status after a short delay to let Redis settle
      setTimeout(fetchCrmStatus, 500);
    } else if (crm && error) {
      showToast(`Failed to connect ${crm === "hubspot" ? "HubSpot" : "Salesforce"}: ${error}`, "error");
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleConnect = (crm: "hubspot" | "salesforce") => {
    // Redirect to backend OAuth initiation URL
    window.location.href = `${BACKEND_URL}/api/crm/${crm}/connect`;
  };

  const handleDisconnect = async (crm: "hubspot" | "salesforce") => {
    setCrmLoading(crm);
    try {
      await api.crmDisconnect(crm);
      await fetchCrmStatus();
      showToast(`${crm === "hubspot" ? "HubSpot" : "Salesforce"} disconnected`, "success");
    } catch {
      showToast(`Failed to disconnect ${crm}`, "error");
    } finally {
      setCrmLoading(null);
    }
  };

  // Static sections
  const staticSections = [
    {
      icon: Key,
      title: "API Keys",
      description: "Manage your Anthropic, SendGrid, and enrichment API keys.",
      items: [
        { name: "Anthropic Claude", status: "configured" },
        { name: "SendGrid", status: "configured" },
        { name: "NewsAPI", status: "configured" },
        { name: "BuiltWith", status: "configured" },
      ],
    },
    {
      icon: Shield,
      title: "Agent Behaviour",
      description: "Control how the agent acts.",
      items: [
        { name: "Autopilot Mode", status: "off" },
        { name: "Confidence Threshold", status: "65%" },
      ],
    },
    {
      icon: Mail,
      title: "Sender Identity",
      description: "Email from address and signature.",
      items: [
        { name: "From Email", status: "outreach@example.com" },
        { name: "Physical Address", status: "configured" },
      ],
    },
  ];

  return (
    <div className="space-y-6 max-w-3xl">
      {toast && <Toast message={toast.message} type={toast.type} />}

      <div>
        <h1 className="text-2xl font-bold mb-1">Settings</h1>
        <p className="text-sm text-textMuted">
          Configure your agent, API keys, and integrations.
        </p>
      </div>

      <div className="space-y-4">
        {/* API Keys — static */}
        {staticSections.slice(0, 1).map((s) => {
          const Icon = s.icon;
          return (
            <div key={s.title} className="card">
              <div className="flex items-start gap-3 mb-3">
                <div className="p-2 bg-accent/15 rounded-md text-accent">
                  <Icon className="w-4 h-4" />
                </div>
                <div>
                  <div className="font-semibold">{s.title}</div>
                  <div className="text-xs text-textMuted">{s.description}</div>
                </div>
              </div>
              <div className="space-y-2 ml-12">
                {s.items.map((item) => (
                  <div
                    key={item.name}
                    className="flex items-center justify-between text-sm border-b border-border/30 pb-2 last:border-0"
                  >
                    <span>{item.name}</span>
                    <span className="text-xs text-textMuted">{item.status}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}

        {/* CRM Connections — live */}
        <div className="card">
          <div className="flex items-start gap-3 mb-3">
            <div className="p-2 bg-accent/15 rounded-md text-accent">
              <Database className="w-4 h-4" />
            </div>
            <div>
              <div className="font-semibold">CRM Connections</div>
              <div className="text-xs text-textMuted">
                Connect your CRM to automatically sync leads.
              </div>
            </div>
          </div>
          <div className="space-y-2 ml-12">
            <CrmRow
              name="HubSpot"
              crmKey="hubspot"
              status={crmStatus?.hubspot ?? null}
              onConnect={handleConnect}
              onDisconnect={handleDisconnect}
              loading={crmLoading === "hubspot"}
            />
            <CrmRow
              name="Salesforce"
              crmKey="salesforce"
              status={crmStatus?.salesforce ?? null}
              onConnect={handleConnect}
              onDisconnect={handleDisconnect}
              loading={crmLoading === "salesforce"}
            />
          </div>
        </div>

        {/* Agent Behaviour + Sender Identity — static */}
        {staticSections.slice(1).map((s) => {
          const Icon = s.icon;
          return (
            <div key={s.title} className="card">
              <div className="flex items-start gap-3 mb-3">
                <div className="p-2 bg-accent/15 rounded-md text-accent">
                  <Icon className="w-4 h-4" />
                </div>
                <div>
                  <div className="font-semibold">{s.title}</div>
                  <div className="text-xs text-textMuted">{s.description}</div>
                </div>
              </div>
              <div className="space-y-2 ml-12">
                {s.items.map((item) => (
                  <div
                    key={item.name}
                    className="flex items-center justify-between text-sm border-b border-border/30 pb-2 last:border-0"
                  >
                    <span>{item.name}</span>
                    <span className="text-xs text-textMuted">{item.status}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
