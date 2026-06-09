"use client";

import { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { api } from "@/lib/api";
import { TrendingUp } from "lucide-react";

export function ReplyRateChart() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.weeklyReplyRate(8).then((d) => {
      setData(
        d.map((w) => ({
          week: w.week_label.replace("Week of ", "").slice(5), // "MM-DD" format
          rate: Number((w.reply_rate * 100).toFixed(1)),
          sent: w.sent,
          replied: w.replied,
        }))
      );
      setLoading(false);
    });
  }, []);

  const latest = data[data.length - 1]?.rate ?? 0;
  const prev = data[data.length - 2]?.rate ?? 0;
  const delta = latest - prev;

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="bg-surface border border-border rounded-lg px-3 py-2 text-xs shadow-lg">
        <div className="font-semibold mb-1">{label}</div>
        <div className="text-accent font-bold">{payload[0]?.value}% reply rate</div>
        <div className="text-textMuted">{payload[0]?.payload?.replied} replied / {payload[0]?.payload?.sent} sent</div>
      </div>
    );
  };

  return (
    <div className="card">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-semibold text-base">Reply Rate Trend</h3>
          <p className="text-xs text-textMuted mt-0.5">Last 8 weeks · agent is learning</p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-accent">{latest}%</div>
          <div className={`text-xs flex items-center gap-1 justify-end ${delta >= 0 ? "text-success" : "text-danger"}`}>
            <TrendingUp className="w-3 h-3" />
            {delta >= 0 ? "+" : ""}{delta.toFixed(1)}% vs last week
          </div>
        </div>
      </div>

      {loading ? (
        <div className="h-[280px] bg-surface2 animate-pulse rounded-lg" />
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
            <XAxis
              dataKey="week"
              stroke="#94A3B8"
              tick={{ fontSize: 11, fill: "#94A3B8" }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              stroke="#94A3B8"
              tick={{ fontSize: 11, fill: "#94A3B8" }}
              unit="%"
              tickLine={false}
              axisLine={false}
              domain={[0, "auto"]}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={5} stroke="#334155" strokeDasharray="3 3" label={{ value: "5%", fill: "#64748b", fontSize: 10 }} />
            <Line
              type="monotone"
              dataKey="rate"
              stroke="#3B82F6"
              strokeWidth={2.5}
              dot={{ fill: "#3B82F6", r: 4, strokeWidth: 0 }}
              activeDot={{ r: 6, fill: "#3B82F6" }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
