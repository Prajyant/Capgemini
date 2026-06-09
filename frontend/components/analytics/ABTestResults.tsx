"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Trophy, FlaskConical } from "lucide-react";
import { formatPercent } from "@/lib/utils";

export function ABTestResults() {
  const [tests, setTests] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.abTests().then((t) => { setTests(t); setLoading(false); });
  }, []);

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <FlaskConical className="w-4 h-4 text-accent" />
        <h3 className="font-semibold text-base">A/B Test Results</h3>
        <span className="ml-auto text-xs text-textMuted">{tests.length} tests</span>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[1, 2].map((i) => <div key={i} className="h-16 bg-surface2 animate-pulse rounded" />)}
        </div>
      ) : tests.length === 0 ? (
        <div className="text-center text-textMuted text-sm py-8">
          No A/B tests yet. Tests run automatically as emails are sent.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[600px]">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-textMuted border-b border-border">
                <th className="py-3 px-3">Variant A (Problem hook)</th>
                <th className="py-3 px-3 text-right">Reply %</th>
                <th className="py-3 px-3">Variant B (Insight hook)</th>
                <th className="py-3 px-3 text-right">Reply %</th>
                <th className="py-3 px-3 text-center">Winner</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/40">
              {tests.map((t, i) => {
                const aWins = t.winner === "A";
                const bWins = t.winner === "B";
                return (
                  <tr key={i} className="hover:bg-surface2/40 transition-colors">
                    <td className="py-3 px-3">
                      <div className={`text-xs max-w-[200px] ${aWins ? "font-semibold text-textPrimary" : "text-textMuted"}`}>
                        {t.variant_a_subject || "Variant A"}
                      </div>
                    </td>
                    <td className="py-3 px-3 text-right tabular-nums font-medium">
                      <span className={aWins ? "text-success" : "text-textMuted"}>
                        {formatPercent(t.variant_a_reply_rate)}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <div className={`text-xs max-w-[200px] ${bWins ? "font-semibold text-textPrimary" : "text-textMuted"}`}>
                        {t.variant_b_subject || "Variant B"}
                      </div>
                    </td>
                    <td className="py-3 px-3 text-right tabular-nums font-medium">
                      <span className={bWins ? "text-success" : "text-textMuted"}>
                        {formatPercent(t.variant_b_reply_rate)}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-center">
                      {t.winner ? (
                        <span className="inline-flex items-center gap-1 badge bg-success/15 text-success border border-success/30">
                          <Trophy className="w-3 h-3" />
                          Variant {t.winner}
                        </span>
                      ) : (
                        <span className="text-textMuted text-xs">Testing...</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
