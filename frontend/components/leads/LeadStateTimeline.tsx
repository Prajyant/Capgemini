"use client";

import { useState } from "react";
import { Check, X, Send, Mail, ChevronDown, ChevronUp } from "lucide-react";
import { AgentDecision } from "@/lib/types";
import { AgentReasoningPanel } from "@/components/dashboard/AgentReasoningPanel";
import { api } from "@/lib/api";

const DECISION_LABELS: Record<string, string> = {
  send_email: "Send Follow-up Email",
  send_linkedin_dm: "Send LinkedIn Message",
  suggest_call: "Schedule a Call",
  wait: "Wait & Monitor",
  escalate_to_human: "Needs Human Review",
  close_sequence: "Close Outreach",
};

export function LeadStateTimeline({
  decisions,
  onUpdate,
}: {
  decisions: AgentDecision[];
  onUpdate?: () => void;
}) {
  const [showAll, setShowAll] = useState(false);

  if (!decisions || decisions.length === 0) {
    return (
      <div className="card text-center text-textMuted py-8">
        No agent reasoning history for this lead yet.
      </div>
    );
  }

  // Show only latest pending + approved/executed ones by default
  const latestPending = decisions.find(
    (d) => d.was_approved == null && !d.executed_at
  );
  const actedUpon = decisions.filter(
    (d) => d.was_approved != null || d.executed_at
  );
  const visibleDecisions = showAll
    ? decisions
    : [...(latestPending ? [latestPending] : []), ...actedUpon];

  const hiddenCount = decisions.length - visibleDecisions.length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-sm flex items-center gap-2">
          <span className="w-1 h-4 bg-accent rounded-full" />
          Agent Decisions
        </h3>
        {hiddenCount > 0 && (
          <button
            onClick={() => setShowAll(!showAll)}
            className="text-xs text-accent hover:underline flex items-center gap-1"
          >
            {showAll ? (
              <><ChevronUp className="w-3 h-3" />Show less</>
            ) : (
              <><ChevronDown className="w-3 h-3" />Show {hiddenCount} older</>
            )}
          </button>
        )}
      </div>

      <div className="space-y-3">
        {visibleDecisions.map((d) => (
          <DecisionCard key={d.id} decision={d} onUpdate={onUpdate} />
        ))}
      </div>
    </div>
  );
}

function DecisionCard({
  decision,
  onUpdate,
}: {
  decision: AgentDecision;
  onUpdate?: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const awaiting = decision.was_approved == null && !decision.executed_at;
  const label = DECISION_LABELS[decision.decision_type] || decision.decision_type;

  const statusBadge = decision.was_approved === true
    ? <span className="badge bg-success/15 text-success border border-success/30 text-[10px]">approved</span>
    : decision.was_approved === false
    ? <span className="badge bg-danger/15 text-danger border border-danger/30 text-[10px]">overridden</span>
    : <span className="badge bg-warning/15 text-warning border border-warning/30 text-[10px]">pending</span>;

  return (
    <div className={`card ${awaiting ? "border-accent/40" : "border-border"}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm">{label}</span>
          {statusBadge}
        </div>
        <span className="text-[10px] text-textMuted">
          {decision.created_at ? new Date(decision.created_at).toLocaleString() : ""}
        </span>
      </div>

      {/* Summary */}
      <p className="text-sm text-textPrimary leading-relaxed mb-3">
        {decision.reasoning_summary}
      </p>

      {/* Confidence bar */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs text-textMuted">Confidence:</span>
        <div className="flex-1 h-2 bg-surface2 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full ${
              Number(decision.confidence_score) >= 0.75
                ? "bg-success"
                : Number(decision.confidence_score) >= 0.5
                ? "bg-warning"
                : "bg-danger"
            }`}
            style={{ width: `${Number(decision.confidence_score) * 100}%` }}
          />
        </div>
        <span className="text-xs font-medium">
          {Math.round(Number(decision.confidence_score) * 100)}%
        </span>
      </div>

      {/* Actions for pending decisions */}
      {awaiting && <DecisionActions decision={decision} onUpdate={onUpdate} />}

      {/* Technical details dropdown */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="mt-2 flex items-center gap-1 text-xs text-textMuted hover:text-accent"
      >
        {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        {expanded ? "Hide" : "Show"} technical details
      </button>
      {expanded && (
        <div className="mt-3 pt-3 border-t border-border">
          <AgentReasoningPanel decision={decision} />
        </div>
      )}
    </div>
  );
}

function DecisionActions({
  decision,
  onUpdate,
}: {
  decision: AgentDecision;
  onUpdate?: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<{
    subject: string;
    body: string;
    sequence_type: string;
  } | null>(null);
  const [previewing, setPreviewing] = useState(false);

  const showPreview = async () => {
    setPreviewing(true);
    try {
      const data = await api.previewEmail(decision.id);
      setPreview(data);
    } catch (e) {
      console.error(e);
      alert("Preview generation failed");
    } finally {
      setPreviewing(false);
    }
  };

  const approve = async () => {
    setLoading(true);
    try {
      await api.approveDecision(decision.id);
      setPreview(null);
      onUpdate?.();
    } catch (e) {
      console.error(e);
      alert("Approve failed — check backend logs");
    } finally {
      setLoading(false);
    }
  };

  const override = async () => {
    setLoading(true);
    try {
      await api.overrideDecision(decision.id, "wait");
      onUpdate?.();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      {/* Email Preview */}
      {decision.decision_type === "send_email" && preview && (
        <div className="bg-surface2 border border-border rounded-md p-3 space-y-2">
          <div className="text-xs uppercase tracking-wide text-accent font-semibold">
            Email Draft
          </div>
          <div className="text-sm font-medium">{preview.subject}</div>
          <div className="text-xs text-textPrimary whitespace-pre-wrap leading-relaxed border-l-2 border-accent/40 pl-3">
            {preview.body}
          </div>
        </div>
      )}

      <div className="flex gap-2 flex-wrap">
        {decision.decision_type === "send_email" && !preview && (
          <button
            onClick={showPreview}
            disabled={previewing || loading}
            className="btn-ghost text-xs py-1.5 px-3 flex items-center gap-1.5 border border-accent text-accent disabled:opacity-50"
          >
            <Mail className="w-3 h-3" />
            {previewing ? "Generating..." : "Preview Email"}
          </button>
        )}
        <button
          onClick={approve}
          disabled={loading}
          className="btn-primary text-xs py-1.5 px-3 flex items-center gap-1.5 disabled:opacity-50"
        >
          {decision.decision_type === "send_email" ? (
            <><Send className="w-3 h-3" />{loading ? "Sending..." : "Approve & Send"}</>
          ) : (
            <><Check className="w-3 h-3" />{loading ? "Approving..." : "Approve"}</>
          )}
        </button>
        <button
          onClick={override}
          disabled={loading}
          className="btn-ghost text-xs py-1.5 px-3 flex items-center gap-1.5 disabled:opacity-50"
        >
          <X className="w-3 h-3" />
          Override
        </button>
      </div>
    </div>
  );
}
