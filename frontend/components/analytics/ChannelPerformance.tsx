"use client";

import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { api } from "@/lib/api";

export function ChannelPerformance() {
  const [data, setData] = useState<any[]>([]);

  useEffect(() => {
    api.channels().then((c) => {
      setData(
        c.map((ch: any) => ({
          channel: ch.channel,
          rate: Number((ch.engagement_rate * 100).toFixed(2)),
          sent: ch.sent,
        }))
      );
    });
  }, []);

  const colors = ["#3B82F6", "#06B6D4", "#8B5CF6"];

  return (
    <div className="card">
      <h3 className="font-semibold mb-3">Channel Performance</h3>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis type="number" stroke="#94A3B8" tick={{ fontSize: 11 }} unit="%" />
          <YAxis type="category" dataKey="channel" stroke="#94A3B8" tick={{ fontSize: 11 }} />
          <Tooltip
            contentStyle={{ backgroundColor: "#1E293B", border: "1px solid #334155", borderRadius: 6 }}
          />
          <Bar dataKey="rate" radius={[0, 4, 4, 0]}>
            {data.map((_, i) => <Cell key={i} fill={colors[i] || "#3B82F6"} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
