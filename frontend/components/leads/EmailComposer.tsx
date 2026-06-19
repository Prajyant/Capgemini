"use client";

import { useState } from "react";
import { Mail, Send, Sparkles, X, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

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
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sentOk, setSentOk] = useState(false);

  const generateDraft = async () => {
    setDrafting(true);
    setError(null);
    setSentOk(false);
    setOpen(true);
    try {
      const draft = await api.draftEmail(leadId);
      setSubject(draft.subject || "");
      setBody(draft.body || "");
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
    setSending(true);
    setError(null);
    try {
      await api.sendEmail(leadId, { subject, body });
      setSentOk(true);
      setTimeout(() => {
        setOpen(false);
        setSentOk(false);
        onSent?.();
      }, 1200);
    } catch (e: any) {
      setError(e?.message || "Failed to send email");
    } finally {
      setSending(false);
    }
  };

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

            <div className="text-xs text-textMuted mb-3">
              To: <span className="text-textPrimary">{leadEmail}</span>
            </div>

            {drafting ? (
              <div className="flex flex-col items-center justify-center py-12 text-textMuted">
                <Loader2 className="w-6 h-6 animate-spin mb-2" />
                <span className="text-sm">AI is drafting a personalized email...</span>
              </div>
            ) : (
              <>
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
                {sentOk && (
                  <div className="text-xs text-success mb-3">
                    ✓ Email sent successfully!
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
                    disabled={sending || drafting || sentOk}
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
