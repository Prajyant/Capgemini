"use client";

import { useState } from "react";
import { CSVUploader } from "@/components/leads/CSVUploader";
import { Database, Upload } from "lucide-react";

export default function ImportPage() {
  const [tab, setTab] = useState<"csv" | "crm">("csv");

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold mb-1">Import Leads</h1>
        <p className="text-sm text-textMuted">
          Upload a CSV or connect your CRM. Enrichment runs automatically.
        </p>
      </div>

      <div className="flex gap-2 border-b border-border">
        <button
          onClick={() => setTab("csv")}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px flex items-center gap-2 ${
            tab === "csv" ? "border-accent text-accent" : "border-transparent text-textMuted hover:text-textPrimary"
          }`}
        >
          <Upload className="w-4 h-4" />
          CSV Upload
        </button>
        <button
          onClick={() => setTab("crm")}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px flex items-center gap-2 ${
            tab === "crm" ? "border-accent text-accent" : "border-transparent text-textMuted hover:text-textPrimary"
          }`}
        >
          <Database className="w-4 h-4" />
          CRM Connect
        </button>
      </div>

      {tab === "csv" && <CSVUploader />}

      {tab === "crm" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="card opacity-90">
            <div className="flex items-center justify-between mb-1">
              <div className="font-semibold">HubSpot</div>
              <span className="badge bg-surface2 border border-border text-textMuted">
                Coming soon
              </span>
            </div>
            <div className="text-xs text-textMuted mb-3">
              Sync contacts and companies from your HubSpot account. Set
              HUBSPOT_CLIENT_ID and HUBSPOT_CLIENT_SECRET in your .env to enable.
            </div>
            <button className="btn-ghost w-full" disabled>
              Connect HubSpot
            </button>
          </div>
          <div className="card opacity-90">
            <div className="flex items-center justify-between mb-1">
              <div className="font-semibold">Salesforce</div>
              <span className="badge bg-surface2 border border-border text-textMuted">
                Coming soon
              </span>
            </div>
            <div className="text-xs text-textMuted mb-3">
              Import leads and accounts from Salesforce. Set
              SALESFORCE_CLIENT_ID and SALESFORCE_CLIENT_SECRET in your .env to
              enable.
            </div>
            <button className="btn-ghost w-full" disabled>
              Connect Salesforce
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
