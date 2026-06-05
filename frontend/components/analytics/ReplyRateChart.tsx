"use client";

import { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";
import { api } from "@/lib/api";

export function ReplyRateChart() {
  const [data, setData] = useState<any[]>([]);

  useEffect(() => {
    api.weeklyReplyRate(8).then((d) => {
      setData(
        d.map((w) => ({
          week: w.week_label.replace("Week of ", ""),
          rate: Number((w.reply_rate * 100).toFixed(2)),
          sent: w.sent,
          replied: w.replied,
        }))
      );
    });
  }, []);

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold">Reply Rate Trend</h3>
        <span className="text-xs text-textMuted">Last 8 weeks · self-improving</span>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="week" stroke="#94A3B8" tick={{ fontSize: 11 }} />
          <YAxis stroke="#94A3B8" tick={{ fontSize: 11 }} unit="%" />
          <Tooltip
            contentStyle={{ backgroundColor: "#1E293B", border: "1px solid #334155", borderRadius: 6 }}
            labelStyle={{ color: "#F1F5F9" }}
          />
          <Line
            type="monotone"
            dataKey="rate"
            stroke="#3B82F6"
            strokeWidth={2.5}
            dot={{ fill: "#3B82F6", r: 4 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
