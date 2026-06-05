"use client";

import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { api } from "@/lib/api";

const COLORS = ["#3B82F6", "#06B6D4", "#8B5CF6", "#F59E0B", "#10B981"];

export function FunnelChart() {
  const [data, setData] = useState<any[]>([]);

  useEffect(() => {
    api.funnel().then((f) => {
      setData([
        { stage: "Sent", count: f.sent },
        { stage: "Delivered", count: f.delivered },
        { stage: "Opened", count: f.opened },
        { stage: "Clicked", count: f.clicked },
        { stage: "Replied", count: f.replied },
      ]);
    });
  }, []);

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold">Email Funnel</h3>
        <span className="text-xs text-textMuted">All time</span>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="stage" stroke="#94A3B8" tick={{ fontSize: 11 }} />
          <YAxis stroke="#94A3B8" tick={{ fontSize: 11 }} />
          <Tooltip
            contentStyle={{ backgroundColor: "#1E293B", border: "1px solid #334155", borderRadius: 6 }}
          />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i] || "#3B82F6"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
