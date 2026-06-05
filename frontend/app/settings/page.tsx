"use client";

import { Key, Database, Mail, Shield } from "lucide-react";

export default function SettingsPage() {
  const sections = [
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
      icon: Database,
      title: "CRM Connections",
      description: "Connect your CRM to automatically sync leads.",
      items: [
        { name: "HubSpot", status: "not connected" },
        { name: "Salesforce", status: "not connected" },
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
      <div>
        <h1 className="text-2xl font-bold mb-1">Settings</h1>
        <p className="text-sm text-textMuted">
          Configure your agent, API keys, and integrations.
        </p>
      </div>

      <div className="space-y-4">
        {sections.map((s) => {
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
                  <div key={item.name} className="flex items-center justify-between text-sm border-b border-border/30 pb-2 last:border-0">
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
