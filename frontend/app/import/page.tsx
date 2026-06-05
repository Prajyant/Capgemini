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
          <div className="card">
            <div className="font-semibold mb-1">HubSpot</div>
            <div className="text-xs text-textMuted mb-3">
              Sync contacts and companies from your HubSpot account.
            </div>
            <button className="btn-primary w-full">Connect HubSpot</button>
          </div>
          <div className="card">
            <div className="font-semibold mb-1">Salesforce</div>
            <div className="text-xs text-textMuted mb-3">
              Import leads and accounts from Salesforce.
            </div>
            <button className="btn-primary w-full">Connect Salesforce</button>
          </div>
        </div>
      )}
    </div>
  );
}
