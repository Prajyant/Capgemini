"use client";

import { useState } from "react";
import { CSVUploader } from "@/components/leads/CSVUploader";
import { Database, Upload, Download, Info } from "lucide-react";

const SAMPLE_CSV = `email,first_name,last_name,job_title,seniority_level,company_name,company_domain,industry,employee_count,linkedin_url,phone
john.smith@hubspot.com,John,Smith,VP of Sales,VP,HubSpot,hubspot.com,SaaS,4000,https://linkedin.com/in/john-smith,+1-617-555-0101
priya.sharma@notion.so,Priya,Sharma,Head of Growth,Director,Notion,notion.so,SaaS,500,https://linkedin.com/in/priya-sharma,
alex.chen@stripe.com,Alex,Chen,CTO,C-Level,Stripe,stripe.com,Fintech,7000,https://linkedin.com/in/alex-chen,+1-415-555-0102
sarah.jones@linear.app,Sarah,Jones,Founder,C-Level,Linear,linear.app,Developer Tools,100,https://linkedin.com/in/sarah-jones,
marcus.brown@figma.com,Marcus,Brown,Sales Director,Director,Figma,figma.com,Design Tools,1000,https://linkedin.com/in/marcus-brown,+1-415-555-0103`;

function downloadSampleCsv() {
  const blob = new Blob([SAMPLE_CSV], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "sample-leads.csv";
  a.click();
  URL.revokeObjectURL(url);
}

export default function ImportPage() {
  const [tab, setTab] = useState<"csv" | "crm">("csv");

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold mb-1">Import Leads</h1>
        <p className="text-sm text-textMuted">
          Upload a CSV with real contacts. Enrichment (news, tech stack, intent) runs automatically after import.
        </p>
      </div>

      <div className="flex gap-2 border-b border-border">
        {[
          { id: "csv", label: "CSV Upload", icon: Upload },
          { id: "crm", label: "CRM Connect", icon: Database },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id as any)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px flex items-center gap-2 transition-colors ${
              tab === id
                ? "border-accent text-accent"
                : "border-transparent text-textMuted hover:text-textPrimary"
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {tab === "csv" && (
        <div className="space-y-5">
          {/* Format guide */}
          <div className="card border-accent/30 bg-accent/5">
            <div className="flex items-start gap-3">
              <Info className="w-4 h-4 text-accent shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-sm mb-2">CSV Format Guide</div>
                <div className="text-xs text-textMuted space-y-1.5">
                  <div>
                    <span className="text-danger font-medium">Required:</span>{" "}
                    <code className="bg-surface2 px-1 rounded text-textPrimary">email</code>
                  </div>
                  <div>
                    <span className="text-success font-medium">Strongly recommended</span>{" "}
                    (needed for real enrichment):{" "}
                    <code className="bg-surface2 px-1 rounded text-textPrimary">company_domain</code>,{" "}
                    <code className="bg-surface2 px-1 rounded text-textPrimary">first_name</code>,{" "}
                    <code className="bg-surface2 px-1 rounded text-textPrimary">company_name</code>
                  </div>
                  <div>
                    <span className="text-textMuted font-medium">Optional:</span>{" "}
                    <code className="bg-surface2 px-1 rounded text-textPrimary">last_name</code>,{" "}
                    <code className="bg-surface2 px-1 rounded text-textPrimary">job_title</code>,{" "}
                    <code className="bg-surface2 px-1 rounded text-textPrimary">seniority_level</code>,{" "}
                    <code className="bg-surface2 px-1 rounded text-textPrimary">industry</code>,{" "}
                    <code className="bg-surface2 px-1 rounded text-textPrimary">employee_count</code>,{" "}
                    <code className="bg-surface2 px-1 rounded text-textPrimary">linkedin_url</code>,{" "}
                    <code className="bg-surface2 px-1 rounded text-textPrimary">phone</code>
                  </div>
                  <div className="pt-1 text-[11px] leading-relaxed">
                    <strong className="text-textPrimary">For real enrichment:</strong> Use real company domains
                    (e.g. <code className="bg-surface2 px-1 rounded">hubspot.com</code>,{" "}
                    <code className="bg-surface2 px-1 rounded">stripe.com</code>). The agent will fetch
                    live news from Google News and scan the company website for tech stack signals.
                  </div>
                </div>
                <button
                  onClick={downloadSampleCsv}
                  className="mt-3 flex items-center gap-1.5 text-xs text-accent hover:underline"
                >
                  <Download className="w-3 h-3" />
                  Download sample CSV (5 real companies)
                </button>
              </div>
            </div>
          </div>

          <CSVUploader />
        </div>
      )}

      {tab === "crm" && (
        <div className="space-y-4">
          <div className="card border-warning/30 bg-warning/5 text-xs text-textMuted">
            <div className="flex items-start gap-2">
              <Info className="w-4 h-4 text-warning shrink-0 mt-0.5" />
              <div>
                CRM OAuth requires setting{" "}
                <code className="bg-surface2 px-1 rounded">HUBSPOT_CLIENT_ID</code> and{" "}
                <code className="bg-surface2 px-1 rounded">HUBSPOT_CLIENT_SECRET</code> in your{" "}
                <code className="bg-surface2 px-1 rounded">.env</code> file. CSV import is the fastest path for demos.
              </div>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { name: "HubSpot", desc: "Sync contacts and companies from your HubSpot CRM.", action: "Connect HubSpot" },
              { name: "Salesforce", desc: "Import leads and accounts from Salesforce.", action: "Connect Salesforce" },
            ].map((crm) => (
              <div key={crm.name} className="card">
                <div className="font-semibold mb-1">{crm.name}</div>
                <div className="text-xs text-textMuted mb-4">{crm.desc}</div>
                <button className="btn-primary w-full">{crm.action}</button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
