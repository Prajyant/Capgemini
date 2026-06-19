"use client";

import { useState } from "react";
import { Sparkles, Check, X, Database, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";

/**
 * One-click loader that replaces the old `demo_send.py` terminal script.
 *
 * Wipes any existing leads (configurable) and seeds 15 richly enriched
 * demo leads so the agent can write the first email straight from the
 * dashboard / lead detail page — no script required.
 */
export function DemoSeedPanel() {
  const [wipe, setWipe] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ created: number; wiped: boolean } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);

  const seed = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const r = await api.seedDemoLeads(wipe);
      setResult({ created: r.created, wiped: r.wiped });
    } catch (e: any) {
      setError(e?.message || "Failed to seed demo leads");
    } finally {
      setLoading(false);
      setConfirming(false);
    }
  };

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-2">
        <div className="p-2 rounded-md bg-accent/15 text-accent">
          <Database className="w-4 h-4" />
        </div>
        <div>
          <div className="font-semibold">Load Demo Leads</div>
          <div className="text-xs text-textMuted">
            Bootstrap a 15-lead pipeline with rich enrichment so the agent can
            draft and send the first email from the dashboard.
          </div>
        </div>
      </div>

      <label className="flex items-center gap-2 text-xs text-textMuted mb-3 mt-4">
        <input
          type="checkbox"
          checked={wipe}
          onChange={(e) => setWipe(e.target.checked)}
          className="accent-accent"
        />
        Wipe all existing leads, email events and decisions first
      </label>

      {wipe && confirming && (
        <div className="flex items-start gap-2 text-xs text-amber-300 bg-amber-500/10 border border-amber-500/30 rounded-md p-2 mb-3">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>
            This will permanently delete every lead, email event and agent
            decision currently in the database. Continue?
          </span>
        </div>
      )}

      <div className="flex items-center gap-2">
        {!confirming || !wipe ? (
          <button
            onClick={() => (wipe ? setConfirming(true) : seed())}
            disabled={loading}
            className="btn-primary flex items-center gap-2 text-sm disabled:opacity-50"
          >
            <Sparkles className="w-4 h-4" />
            {loading ? "Seeding..." : "Load Demo Leads"}
          </button>
        ) : (
          <>
            <button
              onClick={seed}
              disabled={loading}
              className="btn-primary flex items-center gap-2 text-sm disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4" />
              {loading ? "Seeding..." : "Yes, wipe & load"}
            </button>
            <button
              onClick={() => setConfirming(false)}
              disabled={loading}
              className="btn-ghost text-sm disabled:opacity-50"
            >
              Cancel
            </button>
          </>
        )}
      </div>

      {result && (
        <div className="mt-4 flex items-center gap-2 text-success text-sm">
          <Check className="w-4 h-4" />
          Created {result.created} demo leads
          {result.wiped ? " (existing data wiped)" : ""}. Open Dashboard or
          Leads to draft and send.
        </div>
      )}
      {error && (
        <div className="mt-4 flex items-center gap-2 text-danger text-sm">
          <X className="w-4 h-4" />
          {error}
        </div>
      )}
    </div>
  );
}
