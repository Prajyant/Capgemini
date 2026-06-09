"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Mail, Linkedin, Phone } from "lucide-react";

const CHANNEL_CONFIG: Record<string, { icon: React.ElementType; label: string; color: string; bar: string }> = {
  email: { icon: Mail, label: "Email", color: "text-blue-300", bar: "bg-blue-500" },
  linkedin: { icon: Linkedin, label: "LinkedIn DM", color: "text-cyan-300", bar: "bg-cyan-500" },
  phone: { icon: Phone, label: "Phone Call", color: "text-purple-300", bar: "bg-purple-500" },
};

export function ChannelPerformance() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.channels().then((c) => {
      setData(c.map((ch: any) => ({
        channel: ch.channel,
        rate: Number((ch.engagement_rate * 100).toFixed(1)),
        sent: ch.sent,
      })));
      setLoading(false);
    });
  }, []);

  const maxRate = Math.max(...data.map((d) => d.rate), 1);

  return (
    <div className="card">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-semibold text-base">Channel Performance</h3>
          <p className="text-xs text-textMuted mt-0.5">Reply rate by outreach channel</p>
        </div>
      </div>

      {loading ? (
        <div className="space-y-4">
          {["email", "linkedin", "phone"].map((c) => (
            <div key={c} className="h-16 bg-surface2 animate-pulse rounded" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {data.map((d) => {
            const cfg = CHANNEL_CONFIG[d.channel] || CHANNEL_CONFIG.email;
            const Icon = cfg.icon;
            return (
              <div key={d.channel} className="bg-surface2/50 rounded-xl border border-border p-4">
                <div className="flex items-center gap-2 mb-3">
                  <div className={`p-2 rounded-md bg-surface2 ${cfg.color}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold">{cfg.label}</div>
                    <div className="text-xs text-textMuted">{d.sent} touchpoints</div>
                  </div>
                </div>
                <div className="text-3xl font-bold tabular-nums mb-2">{d.rate}%</div>
                <div className="text-xs text-textMuted mb-2">reply rate</div>
                <div className="h-2 bg-surface rounded-full overflow-hidden">
                  <div
                    className={`h-full ${cfg.bar} rounded-full transition-all duration-700`}
                    style={{ width: `${maxRate > 0 ? (d.rate / maxRate) * 100 : 0}%` }}
                  />
                </div>
              </div>
            );
          })}
          {data.length === 0 && (
            <div className="col-span-3 text-center text-textMuted text-sm py-8">
              No channel data yet. Start outreach to see performance by channel.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
