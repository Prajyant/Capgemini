"use client";

import { useEffect, useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, LineChart, Line, XAxis, YAxis, CartesianGrid } from "recharts";
import { api } from "@/lib/api";
import { DECISION_LABELS } from "@/lib/utils";

const COLORS: Record<string, string> = {
  send_email: "#3B82F6",
  send_linkedin_dm: "#06B6D4",
  suggest_call: "#8B5CF6",
  wait: "#F59E0B",
  escalate_to_human: "#EF4444",
  close_sequence: "#94A3B8",
};

export function AgentPerformancePanel() {
  const [data, setData] = useState<any | null>(null);

  useEffect(() => {
    api.agentPerformance().then(setData);
  }, []);

  if (!data) return <div className="card animate-pulse h-64" />;

  const breakdown = Object.entries(data.decision_breakdown || {}).map(
    ([k, v]) => ({ name: DECISION_LABELS[k] || k, key: k, value: Number(v) })
  );

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div className="card">
        <h3 className="font-semibold mb-3 text-sm">Decision Breakdown</h3>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={breakdown}
              cx="50%" cy="50%"
              innerRadius={45}
              outerRadius={80}
              dataKey="value"
              paddingAngle={2}
            >
              {breakdown.map((entry, i) => (
                <Cell key={i} fill={COLORS[entry.key] || "#3B82F6"} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ backgroundColor: "#1E293B", border: "1px solid #334155", borderRadius: 6 }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="grid grid-cols-2 gap-1 text-xs">
          {breakdown.map((b) => (
            <div key={b.key} className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full" style={{ background: COLORS[b.key] || "#3B82F6" }} />
              <span className="text-textMuted truncate">{b.name}</span>
              <span className="ml-auto tabular-nums">{b.value}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="card md:col-span-2">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-semibold text-sm">Avg Confidence Trend</h3>
          <span className="text-xs text-textMuted">Last 14 days</span>
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data.avg_confidence_trend}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="date" stroke="#94A3B8" tick={{ fontSize: 10 }} />
            <YAxis stroke="#94A3B8" tick={{ fontSize: 10 }} domain={[0, 1]} />
            <Tooltip
              contentStyle={{ backgroundColor: "#1E293B", border: "1px solid #334155", borderRadius: 6 }}
            />
            <Line type="monotone" dataKey="avg_confidence" stroke="#10B981" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
        <div className="grid grid-cols-3 gap-3 mt-3 text-center">
          <div>
            <div className="text-xs text-textMuted">Avg Confidence</div>
            <div className="font-bold text-success">{(data.avg_confidence * 100).toFixed(0)}%</div>
          </div>
          <div>
            <div className="text-xs text-textMuted">Total Decisions</div>
            <div className="font-bold">{data.total_decisions}</div>
          </div>
          <div>
            <div className="text-xs text-textMuted">Override Rate</div>
            <div className="font-bold text-warning">{(data.human_override_rate * 100).toFixed(1)}%</div>
          </div>
        </div>
      </div>
    </div>
  );
}
