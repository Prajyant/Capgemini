"use client";

import { useEffect, useState } from "react";
import { TrendingUp, TrendingDown, Mail, Brain, Users, Activity } from "lucide-react";
import { api } from "@/lib/api";
import { OverviewKPIs } from "@/lib/types";
import { formatPercent } from "@/lib/utils";

function MetricCard({
  label, value, delta, icon: Icon, suffix,
}: {
  label: string;
  value: string | number;
  delta?: { value: number; isPercent?: boolean } | null;
  icon: React.ElementType;
  suffix?: string;
}) {
  const trendUp = delta && delta.value > 0;
  const trendDown = delta && delta.value < 0;
  return (
    <div className="card flex items-start justify-between">
      <div>
        <div className="text-xs uppercase text-textMuted tracking-wide font-medium">{label}</div>
        <div className="mt-2 text-3xl font-bold">{value}{suffix}</div>
        {delta && (
          <div className={`mt-2 flex items-center gap-1 text-xs ${
            trendUp ? "text-success" : trendDown ? "text-danger" : "text-textMuted"
          }`}>
            {trendUp && <TrendingUp className="w-3 h-3" />}
            {trendDown && <TrendingDown className="w-3 h-3" />}
            <span>
              {delta.value > 0 ? "+" : ""}
              {delta.isPercent ? formatPercent(delta.value) : delta.value}
              {" vs last week"}
            </span>
          </div>
        )}
      </div>
      <div className="p-2 rounded-md bg-accent/15 text-accent">
        <Icon className="w-5 h-5" />
      </div>
    </div>
  );
}

export function MetricsStrip() {
  const [kpis, setKpis] = useState<OverviewKPIs | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setKpis(await api.overview());
      } catch (e) {
        console.error("KPI fetch failed:", e);
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (!kpis) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="card animate-pulse">
            <div className="h-3 bg-surface2 rounded w-24 mb-3" />
            <div className="h-8 bg-surface2 rounded w-16" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <MetricCard
        label="Active Leads"
        value={kpis.total_active_leads}
        delta={{ value: kpis.total_active_leads_delta }}
        icon={Users}
      />
      <MetricCard
        label="Reply Rate (week)"
        value={formatPercent(kpis.reply_rate_week)}
        delta={{ value: kpis.reply_rate_delta, isPercent: true }}
        icon={Activity}
      />
      <MetricCard
        label="Emails Sent Today"
        value={kpis.emails_sent_today}
        icon={Mail}
      />
      <MetricCard
        label="Agent Decisions Today"
        value={kpis.decisions_made_today}
        icon={Brain}
      />
    </div>
  );
}
