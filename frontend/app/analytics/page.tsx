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
          The self-improving loop — every metric feeds back into the agent's decisions.
        </p>
      </div>

      {/* Top row: Reply rate trend (wider) + Funnel */}
      <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-4">
        <ReplyRateChart />
        <FunnelChart />
      </div>

      {/* Second row: Channel performance (full width) */}
      <ChannelPerformance />

      {/* A/B Tests */}
      <ABTestResults />

      {/* Agent performance */}
      <div>
        <h2 className="text-xs font-semibold uppercase tracking-wide text-textMuted mb-3">
          Agent Performance
        </h2>
        <AgentPerformancePanel />
      </div>
    </div>
  );
}
