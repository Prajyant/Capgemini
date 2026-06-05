import { MetricsStrip } from "@/components/dashboard/MetricsStrip";
import { PipelineBoard } from "@/components/dashboard/PipelineBoard";
import { ActivityFeed } from "@/components/dashboard/ActivityFeed";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-1">Dashboard</h1>
        <p className="text-sm text-textMuted">
          Real-time view of the agent reasoning over your pipeline.
        </p>
      </div>

      <MetricsStrip />

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-4">
        <div className="min-w-0">
          <PipelineBoard />
        </div>
        <div className="xl:sticky xl:top-20 xl:h-fit">
          <ActivityFeed />
        </div>
      </div>
    </div>
  );
}
