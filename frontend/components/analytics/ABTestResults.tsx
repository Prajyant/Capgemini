"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Trophy } from "lucide-react";
import { formatPercent } from "@/lib/utils";

export function ABTestResults() {
  const [tests, setTests] = useState<any[]>([]);

  useEffect(() => {
    api.abTests().then(setTests);
  }, []);

  return (
    <div className="card">
      <h3 className="font-semibold mb-3">A/B Test Results</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-textMuted uppercase tracking-wide border-b border-border">
              <th className="py-2">Variant A subject</th>
              <th className="py-2">A reply</th>
              <th className="py-2">Variant B subject</th>
              <th className="py-2">B reply</th>
              <th className="py-2">Winner</th>
            </tr>
          </thead>
          <tbody>
            {tests.length === 0 && (
              <tr><td colSpan={5} className="py-4 text-center text-textMuted">No A/B tests yet</td></tr>
            )}
            {tests.map((t, i) => (
              <tr key={i} className="border-b border-border/50">
                <td className="py-2 max-w-[180px] truncate">{t.variant_a_subject}</td>
                <td className="py-2">{formatPercent(t.variant_a_reply_rate)}</td>
                <td className="py-2 max-w-[180px] truncate">{t.variant_b_subject}</td>
                <td className="py-2">{formatPercent(t.variant_b_reply_rate)}</td>
                <td className="py-2">
                  {t.winner ? (
                    <span className="badge bg-success/20 text-success border border-success/40 flex items-center gap-1 w-fit">
                      <Trophy className="w-3 h-3" />
                      {t.winner}
                    </span>
                  ) : (
                    <span className="text-textMuted">undecided</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
