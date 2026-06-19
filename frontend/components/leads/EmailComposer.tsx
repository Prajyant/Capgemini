"use client";

import { useEffect, useState } from "react";
import { Mail, Send, Sparkles, X, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { getDemoRecipient, onDemoRecipientChange } from "@/lib/demoMode";

/**
 * Compose & send an email for a lead.
 *
 * The "To" field is editable on purpose: during a live demo / pitch the
 * presenter wants the email to arrive in their own inbox so the judges
 * can watch it land. The EmailEvent on the backend is still recorded
 * against the lead either way, so the dashboard / reasoning trail looks
 * exactly like a real send.
 */
export function EmailComposer({
  leadId,
  leadEmail,
  onSent,
}: {
  leadId: string;
  leadEmail: string;
  onSent?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [drafting, setDrafting] = useState(false);
  const [sending, setSending] = useState(false);
  const [toEmail, setToEmail] = useState(leadEmail);
  const [demoRecipient, setLocalDemoRecipient] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sentInfo, setSentInfo] = useState<{ to: string } | null>(null);

  // Hydrate the demo override from localStorage and stay in sync if the
  // presenter changes it from the navbar while this modal is open.
  useEffect(() => {
    setLocalDemoRecipient(getDemoRecipient());
    return onDemoRecipientChange(() => setLocalDemoRecipient(getDemoRecipient()));
  }, []);

  // Default the recipient to the demo override when set, otherwise the
  // lead's real email. Re-applies whenever either input changes.
  useEffect(() => {
    setToEmail(demoRecipient || leadEmail);
  }, [leadEmail, demoRecipient]);

  const generateDraft = async () => {
    setDrafting(true);
    setError(null);
    setSentInfo(null);
    setOpen(true);
    try {
      const draft = await api.draftEmail(leadId);
      setSubject(draft.subject || "");
      setBody(draft.body || "");
      // Recipient defaults to the demo override (if set) or the lead's
      // real email when (re)drafting.
      setToEmail(demoRecipient || leadEmail);
    } catch (e: any) {
      setError(e?.message || "Failed to generate draft");
    } finally {
      setDrafting(false);
    }
  };

  const send = async () => {
    if (!subject.trim() || !body.trim()) {
      setError("Subject and body are required");
      return;
    }
    if (!toEmail.trim() || !toEmail.includes("@")) {
      setError("A valid recipient email is required");
      return;
    }
    setSending(true);
    setError(null);
    try {
      const result = await api.sendEmail(leadId, {
        subject,
        body,
        to_email: toEmail.trim(),
      });
      setSentInfo({ to: result?.delivered_to || toEmail.trim() });
      setTimeout(() => {
        setOpen(false);
        setSentInfo(null);
        onSent?.();
      }, 1400);
    } catch (e: any) {
      setError(e?.message || "Failed to send email");
    } finally {
      setSending(false);
    }
  };

  const baseline = demoRecipient || leadEmail;
  const recipientChanged =
    toEmail.trim().toLowerCase() !== baseline.trim().toLowerCase();

  return (
    <>
      <button
        onClick={generateDraft}
        className="btn-primary flex items-center gap-2 text-sm"
      >
        <Sparkles className="w-4 h-4" />
        Compose Email
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="card w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-surface">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Mail className="w-4 h-4 text-accent" />
                <h3 className="font-semibold">Compose Email</h3>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="text-textMuted hover:text-textPrimary"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {drafting ? (
              <div className="flex flex-col items-center justify-center py-12 text-textMuted">
                <Loader2 className="w-6 h-6 animate-spin mb-2" />
                <span className="text-sm">AI is drafting a personalized email...</span>
              </div>
            ) : (
              <>
                <div className="mb-3">
                  <label className="text-xs text-textMuted block mb-1">
                    To
                  </label>
                  <input
                    value={toEmail}
                    onChange={(e) => setToEmail(e.target.value)}
                    type="email"
                    className="w-full bg-surface2 border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-accent"
                    placeholder="recipient@example.com"
                  />
                  <div className="text-[11px] text-textMuted mt-1 flex items-center justify-between gap-2">
                    <span>
                      Lead's email is{" "}
                      <span className="text-textPrimary">{leadEmail}</span>.
                      {demoRecipient && (
                        <>
                          {" "}Demo override is active —{" "}
                          <span className="text-warning">{demoRecipient}</span>.
                        </>
                      )}
                    </span>
                    {recipientChanged && (
                      <button
                        type="button"
                        onClick={() => setToEmail(demoRecipient || leadEmail)}
                        className="text-accent hover:underline shrink-0"
                      >
                        Reset
                      </button>
                    )}
                  </div>
                </div>

                <div className="mb-3">
                  <label className="text-xs text-textMuted block mb-1">Subject</label>
                  <input
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    className="w-full bg-surface2 border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-accent"
                    placeholder="Email subject"
                  />
                </div>
                <div className="mb-4">
                  <label className="text-xs text-textMuted block mb-1">Body</label>
                  <textarea
                    value={body}
                    onChange={(e) => setBody(e.target.value)}
                    rows={12}
                    className="w-full bg-surface2 border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-accent font-mono resize-y"
                    placeholder="Email body"
                  />
                </div>

                {error && (
                  <div className="text-xs text-danger mb-3">{error}</div>
                )}
                {sentInfo && (
                  <div className="text-xs text-success mb-3">
                    ✓ Email sent to {sentInfo.to}
                  </div>
                )}

                <div className="flex items-center justify-between gap-2">
                  <button
                    onClick={generateDraft}
                    disabled={drafting || sending}
                    className="btn-secondary flex items-center gap-1 text-xs disabled:opacity-50"
                  >
                    <Sparkles className="w-3 h-3" />
                    Regenerate
                  </button>
                  <button
                    onClick={send}
                    disabled={sending || drafting || !!sentInfo}
                    className="btn-primary flex items-center gap-2 text-sm disabled:opacity-50"
                  >
                    {sending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                    {sending ? "Sending..." : "Send Email"}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
