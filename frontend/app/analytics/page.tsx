import { ReplyRateChart } from "@/components/analytics/ReplyRateChart";
import { FunnelChart } from "@/components/analytics/FunnelChart";
import { ChannelPerformance } from "@/components/analytics/ChannelPerformance";
import { ABTestResults } from "@/components/analytics/ABTestResults";
import { AgentPerformancePanel } from "@/components/analytics/AgentPerformancePanel";

export default function AnalyticsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-1">Analytics</h1>
        <p className="text-sm text-textMuted">
          The self-improving loop made visible.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-1"><ReplyRateChart /></div>
        <div className="lg:col-span-1"><FunnelChart /></div>
        <div className="lg:col-span-1"><ChannelPerformance /></div>
      </div>

      <ABTestResults />

      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-textMuted mb-3">
          Agent Performance
        </h2>
        <AgentPerformancePanel />
      </div>
    </div>
  );
}
