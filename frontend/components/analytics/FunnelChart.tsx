"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const FUNNEL_STAGES = [
  { key: "sent", label: "Sent", color: "bg-blue-500" },
  { key: "delivered", label: "Delivered", color: "bg-cyan-500" },
  { key: "opened", label: "Opened", color: "bg-purple-500" },
  { key: "clicked", label: "Clicked", color: "bg-amber-500" },
  { key: "replied", label: "Replied", color: "bg-emerald-500" },
];

export function FunnelChart() {
  const [data, setData] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.funnel().then((f) => {
      setData(f);
      setLoading(false);
    });
  }, []);

  const max = data.sent || 1;

  return (
    <div className="card">
      <div className="mb-4">
        <h3 className="font-semibold text-base">Email Funnel</h3>
        <p className="text-xs text-textMuted mt-0.5">Conversion at each stage</p>
      </div>

      {loading ? (
        <div className="space-y-3">
          {FUNNEL_STAGES.map((s) => <div key={s.key} className="h-10 bg-surface2 animate-pulse rounded" />)}
        </div>
      ) : (
        <div className="space-y-2.5">
          {FUNNEL_STAGES.map((stage, i) => {
            const count = data[stage.key] ?? 0;
            const pct = max > 0 ? Math.round((count / max) * 100) : 0;
            const prev = i > 0 ? (data[FUNNEL_STAGES[i - 1].key] ?? 0) : max;
            const convRate = prev > 0 ? Math.round((count / prev) * 100) : 0;
            return (
              <div key={stage.key}>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="font-medium text-textPrimary">{stage.label}</span>
                  <div className="flex items-center gap-2">
                    {i > 0 && (
                      <span className="text-textMuted">{convRate}% of prev</span>
                    )}
                    <span className="font-bold tabular-nums text-textPrimary">{count.toLocaleString()}</span>
                  </div>
                </div>
                <div className="h-6 bg-surface2 rounded overflow-hidden">
                  <div
                    className={`h-full ${stage.color} rounded transition-all duration-500 flex items-center`}
                    style={{ width: `${Math.max(pct, 2)}%` }}
                  >
                    {pct > 15 && (
                      <span className="text-white text-[10px] font-bold px-2">{pct}%</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
