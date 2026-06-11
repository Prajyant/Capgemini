"use client";

import { useState } from "react";
import {
  AlertOctagon,
  Mail,
  MailOpen,
  MessageCircle,
  MousePointer2,
  Send,
  ShieldOff,
  Sparkles,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatRelative } from "@/lib/utils";

/** Strip quoted email thread from reply — only show the actual reply text */
function stripQuotedReply(content: string): string {
  const lines = content.split("\n");
  const cleanLines: string[] = [];
  for (const line of lines) {
    // Stop at "On ... wrote:" pattern (may span a line that just starts with "On")
    if (/^On\s.+wrote:/.test(line.trim())) break;
    if (/^On\s+(Mon|Tue|Wed|Thu|Fri|Sat|Sun)/.test(line.trim())) break;
    // Stop at "> " quoted lines
    if (line.trim().startsWith(">")) break;
    // Stop at "---" separator
    if (line.trim() === "---") break;
    // Stop at lines that look like email headers
    if (/^(From|Sent|To|Subject|Date):/.test(line.trim())) break;
    cleanLines.push(line);
  }
  const result = cleanLines.join("\n").trim();
  return result || content.split("\n")[0]; // fallback to first line
}

export type EngagementEvent = {
  id: string;
  event_type: string;
  channel?: string;
  subject?: string | null;
  ab_variant?: string | null;
  clicked_url?: string | null;
  reply_content?: string | null;
  reply_sentiment?: string | null;
  reply_intent?: string | null;
  occurred_at?: string | null;
};

const ICON_BY_TYPE: Record<
  string,
  { Icon: typeof Mail; tint: string; label: string }
> = {
  sent: { Icon: Mail, tint: "text-textMuted", label: "Email sent" },
  delivered: { Icon: Mail, tint: "text-textMuted", label: "Delivered" },
  opened: { Icon: MailOpen, tint: "text-success", label: "Opened" },
  clicked: { Icon: MousePointer2, tint: "text-accent", label: "Clicked" },
  replied: { Icon: MessageCircle, tint: "text-accent", label: "Replied" },
  bounced: { Icon: AlertOctagon, tint: "text-danger", label: "Bounced" },
  spam: { Icon: AlertOctagon, tint: "text-danger", label: "Marked spam" },
  unsubscribed: { Icon: ShieldOff, tint: "text-warning", label: "Unsubscribed" },
};

export function LeadEngagementPanel({
  events,
  leadEmail,
  leadId,
  onSimulated,
}: {
  events: EngagementEvent[];
  leadEmail: string;
  leadId: string;
  onSimulated?: () => void;
}) {
  const openCount = events.filter((e) => e.event_type === "opened").length;
  const clickCount = events.filter((e) => e.event_type === "clicked").length;
  const replyCount = events.filter((e) => e.event_type === "replied").length;
  const sentCount = events.filter((e) => e.event_type === "sent").length;

  return (
    <div className="card">
      {/* Engagement Stats */}
      <div className="flex items-center gap-4 mb-4 pb-3 border-b border-border">
        <div className="flex items-center gap-1.5 text-sm">
          <Mail className="w-3.5 h-3.5 text-textMuted" />
          <span className="font-semibold">{sentCount}</span>
          <span className="text-textMuted text-xs">sent</span>
        </div>
        <div className="flex items-center gap-1.5 text-sm">
          <MailOpen className="w-3.5 h-3.5 text-success" />
          <span className="font-semibold">{openCount}</span>
          <span className="text-textMuted text-xs">opens</span>
        </div>
        <div className="flex items-center gap-1.5 text-sm">
          <MousePointer2 className="w-3.5 h-3.5 text-accent" />
          <span className="font-semibold">{clickCount}</span>
          <span className="text-textMuted text-xs">clicks</span>
        </div>
        <div className="flex items-center gap-1.5 text-sm">
          <MessageCircle className="w-3.5 h-3.5 text-accent" />
          <span className="font-semibold">{replyCount}</span>
          <span className="text-textMuted text-xs">replies</span>
        </div>
      </div>

      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <MessageCircle className="w-4 h-4 text-accent" />
          <h3 className="font-semibold text-sm">Prior Engagement (buyer side)</h3>
        </div>
        <div className="flex items-center gap-1">
          <SimulateEventButtons leadId={leadId} onSimulated={onSimulated} />
          <SimulateReply leadEmail={leadEmail} onSimulated={onSimulated} />
        </div>
      </div>

      {events.length === 0 ? (
        <div className="text-xs text-textMuted text-center py-6">
          No buyer activity yet. Once we send and the buyer opens, clicks, or
          replies, it will appear here.
        </div>
      ) : (
        <ul className="space-y-3">
          {events.map((e) => {
            const meta =
              ICON_BY_TYPE[e.event_type] || {
                Icon: Mail,
                tint: "text-textMuted",
                label: e.event_type,
              };
            const Icon = meta.Icon;
            return (
              <li key={e.id} className="flex gap-3">
                <div
                  className={`w-7 h-7 shrink-0 rounded-full bg-surface2 border border-border flex items-center justify-center ${meta.tint}`}
                >
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 text-sm flex-wrap">
                    <span className="font-medium">{meta.label}</span>
                    {e.subject && (
                      <span className="text-textMuted truncate">
                        — {e.subject}
                      </span>
                    )}
                    {e.ab_variant && (
                      <span className="badge bg-surface2 border border-border">
                        Variant {e.ab_variant}
                      </span>
                    )}
                  </div>

                  {e.event_type === "replied" && e.reply_content && (
                    <div className="mt-1 text-xs text-textPrimary bg-surface2 border border-border rounded p-2 whitespace-pre-wrap">
                      {stripQuotedReply(e.reply_content)}
                    </div>
                  )}

                  {(e.reply_intent || e.reply_sentiment) && (
                    <div className="text-[11px] text-textMuted mt-1">
                      {e.reply_intent && <>Intent: <span className="text-textPrimary">{e.reply_intent}</span></>}
                      {e.reply_sentiment && (
                        <>
                          {" · "}sentiment{" "}
                          <span className="text-textPrimary">
                            {e.reply_sentiment}
                          </span>
                        </>
                      )}
                    </div>
                  )}

                  {e.clicked_url && (
                    <a
                      href={e.clicked_url}
                      target="_blank"
                      rel="noreferrer"
                      className="block text-[11px] text-accent mt-0.5 truncate hover:underline"
                    >
                      {e.clicked_url}
                    </a>
                  )}

                  <div className="text-[10px] text-textMuted mt-0.5">
                    {e.occurred_at ? formatRelative(e.occurred_at) : ""}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function SimulateReply({
  leadEmail,
  onSimulated,
}: {
  leadEmail: string;
  onSimulated?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [body, setBody] = useState(
    "Thanks for reaching out — happy to chat next week. What times work for you?"
  );
  const [subject, setSubject] = useState("Re: your note");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send() {
    if (!body.trim()) {
      setError("Reply body cannot be empty");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.simulateInboundReply({
        from_email: leadEmail,
        subject: subject || undefined,
        body,
      });
      setOpen(false);
      onSimulated?.();
    } catch (e: any) {
      setError(e?.message || "Failed to simulate reply");
    } finally {
      setSubmitting(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="btn-ghost text-xs py-1 px-2 flex items-center gap-1.5"
        title="Simulate an inbound reply from this buyer to test the flow"
      >
        <Sparkles className="w-3.5 h-3.5" />
        Simulate buyer reply
      </button>
    );
  }

  return (
    <div className="absolute right-6 mt-12 w-80 bg-surface border border-border rounded-md shadow-xl p-3 z-20 space-y-2">
      <div className="text-xs font-semibold">Simulate inbound reply</div>
      <input
        className="input"
        value={subject}
        onChange={(e) => setSubject(e.target.value)}
        placeholder="Subject"
        disabled={submitting}
      />
      <textarea
        className="input min-h-[90px]"
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="Reply body"
        disabled={submitting}
      />
      {error && <div className="text-danger text-xs">{error}</div>}
      <div className="flex justify-end gap-2 pt-1">
        <button
          className="btn-ghost text-xs py-1 px-2"
          onClick={() => setOpen(false)}
          disabled={submitting}
        >
          Cancel
        </button>
        <button
          className="btn-primary text-xs py-1 px-2 flex items-center gap-1.5"
          onClick={send}
          disabled={submitting}
        >
          <Send className="w-3.5 h-3.5" />
          {submitting ? "Sending..." : "Send"}
        </button>
      </div>
    </div>
  );
}


function SimulateEventButtons({
  leadId,
  onSimulated,
}: {
  leadId: string;
  onSimulated?: () => void;
}) {
  const [loading, setLoading] = useState<string | null>(null);

  async function simulate(eventType: string) {
    setLoading(eventType);
    try {
      await api.simulateEvent({
        lead_id: leadId,
        event_type: eventType,
        clicked_url: eventType === "clicked" ? "https://example.com/demo" : undefined,
      });
      onSimulated?.();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="flex items-center gap-1">
      <button
        onClick={() => simulate("opened")}
        disabled={!!loading}
        className="btn-ghost text-xs py-1 px-2 flex items-center gap-1"
        title="Simulate email open"
      >
        <MailOpen className="w-3 h-3" />
        {loading === "opened" ? "..." : "Open"}
      </button>
      <button
        onClick={() => simulate("clicked")}
        disabled={!!loading}
        className="btn-ghost text-xs py-1 px-2 flex items-center gap-1"
        title="Simulate link click"
      >
        <MousePointer2 className="w-3 h-3" />
        {loading === "clicked" ? "..." : "Click"}
      </button>
      <button
        onClick={() => simulate("bounced")}
        disabled={!!loading}
        className="btn-ghost text-xs py-1 px-2 flex items-center gap-1"
        title="Simulate bounce"
      >
        <AlertOctagon className="w-3 h-3" />
        {loading === "bounced" ? "..." : "Bounce"}
      </button>
    </div>
  );
}
