"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Workflow, Plus } from "lucide-react";

export default function SequencesPage() {
  const [seqs, setSeqs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listSequences().then((s) => {
      setSeqs(s);
      setLoading(false);
    });
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold mb-1">Sequences</h1>
          <p className="text-sm text-textMuted">
            Multi-touch outreach sequences. Emails are generated per-lead by the agent.
          </p>
        </div>
        <button className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" />
          New Sequence
        </button>
      </div>

      {loading && <div className="text-textMuted">Loading...</div>}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {seqs.map((s) => (
          <div key={s.id} className="card card-hover">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-accent/15 rounded-md text-accent">
                <Workflow className="w-4 h-4" />
              </div>
              <div className="flex-1">
                <div className="font-semibold">{s.name}</div>
                <div className="text-xs text-textMuted">
                  {s.vertical || "All verticals"} · {s.total_steps} steps
                </div>
                <div className="mt-3 flex flex-wrap gap-1">
                  {(s.steps || []).map((step: any) => (
                    <span
                      key={step.id}
                      className="badge bg-surface2 border border-border"
                    >
                      Step {step.step_number}: {step.channel}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
        {!loading && seqs.length === 0 && (
          <div className="card text-center text-textMuted py-12 col-span-2">
            No sequences yet. Create one to get started.
          </div>
        )}
      </div>
    </div>
  );
}
