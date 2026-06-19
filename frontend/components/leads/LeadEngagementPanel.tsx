"use client";

import { useEffect, useState } from "react";
import {
  AlertOctagon,
  Mail,
  MailOpen,
  MessageCircle,
  MousePointer2,
  Send,
  ShieldOff,
  Sparkles,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatRelative } from "@/lib/utils";

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
  onSimulated,
}: {
  events: EngagementEvent[];
  leadEmail: string;
  onSimulated?: () => void;
}) {
  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <MessageCircle className="w-4 h-4 text-accent" />
          <h3 className="font-semibold text-sm">Prior Engagement (buyer side)</h3>
        </div>
        <SimulateReply leadEmail={leadEmail} onSimulated={onSimulated} />
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
                      {e.reply_content}
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

/**
 * Quality-of-life affordance for demos: posts a fake inbound reply through the
 * webhook so we can rehearse the agent's response flow without a real reply.
 *
 * Lives in a centred modal — the previous implementation rendered as a
 * floating popover positioned via `absolute right-6 mt-12`, which routinely
 * landed off-screen on smaller viewports.
 */
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

  // Close with Escape when the modal is open.
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !submitting) setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, submitting]);

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

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="btn-ghost text-xs py-1 px-2 flex items-center gap-1.5"
        title="Simulate an inbound reply from this buyer to test the flow"
      >
        <Sparkles className="w-3.5 h-3.5" />
        Simulate buyer reply
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => !submitting && setOpen(false)}
        >
          <div
            className="bg-surface border border-border rounded-md shadow-xl w-full max-w-md p-4 space-y-3"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <div className="text-sm font-semibold">Simulate inbound reply</div>
              <button
                className="text-textMuted hover:text-textPrimary"
                onClick={() => setOpen(false)}
                disabled={submitting}
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="text-xs text-textMuted">
              From: <span className="text-textPrimary">{leadEmail}</span>
            </div>
            <input
              className="input"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Subject"
              disabled={submitting}
            />
            <textarea
              className="input min-h-[120px] font-sans resize-y"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Reply body"
              disabled={submitting}
            />
            {error && <div className="text-danger text-xs">{error}</div>}
            <div className="flex justify-end gap-2 pt-1">
              <button
                className="btn-ghost text-xs"
                onClick={() => setOpen(false)}
                disabled={submitting}
              >
                Cancel
              </button>
              <button
                className="btn-primary text-xs flex items-center gap-1.5"
                onClick={send}
                disabled={submitting}
              >
                <Send className="w-3.5 h-3.5" />
                {submitting ? "Sending..." : "Send"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
