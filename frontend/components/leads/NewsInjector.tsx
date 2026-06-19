"use client";

import { useState } from "react";
import { Loader2, Newspaper, Plus, Sparkles, X } from "lucide-react";
import { api } from "@/lib/api";

/**
 * "Add demo news" widget.
 *
 * Lets the presenter inject a fake news item against a lead's company
 * during a live demo so the buying-intent score and enrichment score
 * visibly recompute on stage. Quick templates map onto the keyword
 * buckets the intent enricher actually scans for:
 *
 *  - Funding (`raised`, `series x`)        →  +18 to +30 intent
 *  - Hiring  (`hiring`, `expanding team`)  →  +5/+5 per match, up to 25
 *  - Tech    (mentions a competitor tool)  →  +10 per tool, up to 30
 *
 * On submit the backend re-derives intent signals AND recomputes the
 * enrichment score (news bucket caps at 30 = 4 items × 8).
 */
export function NewsInjector({
  leadId,
  companyName,
  onChanged,
}: {
  leadId: string;
  companyName?: string | null;
  onChanged: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [headline, setHeadline] = useState("");
  const [source, setSource] = useState("Demo");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const co = companyName || "the company";

  const TEMPLATES: { label: string; headline: string; source: string }[] = [
    {
      label: "Just raised Series B",
      headline: `${co} raises $40M Series B to accelerate go-to-market`,
      source: "TechCrunch",
    },
    {
      label: "Hiring a sales team",
      headline: `${co} announces hiring 10 SDRs and 3 AEs to scale revenue`,
      source: "LinkedIn",
    },
    {
      label: "Adopted competitor tool",
      headline: `${co} rolls out Outreach.io across the SDR team`,
      source: "Press release",
    },
  ];

  function chooseTemplate(t: (typeof TEMPLATES)[number]) {
    setHeadline(t.headline);
    setSource(t.source);
    setError(null);
  }

  async function submit() {
    if (!headline.trim()) {
      setError("Headline is required");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.addLeadNews(leadId, {
        headline: headline.trim(),
        source: source.trim() || "Demo",
      });
      setOpen(false);
      setHeadline("");
      setSource("Demo");
      onChanged();
    } catch (e: any) {
      setError(e?.message || "Failed to add news");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="btn-ghost flex items-center gap-1.5 text-xs"
        title="Add a fake news item to demo how scores react to fresh signals"
      >
        <Plus className="w-3.5 h-3.5" />
        Add demo news
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => !submitting && setOpen(false)}
        >
          <div
            className="bg-surface border border-border rounded-md shadow-xl w-full max-w-lg p-4 space-y-3"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <Newspaper className="w-4 h-4 text-accent" />
                Inject a news item
              </div>
              <button
                onClick={() => setOpen(false)}
                disabled={submitting}
                className="text-textMuted hover:text-textPrimary"
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-xs text-textMuted leading-relaxed">
              Adding news for <span className="text-textPrimary">{co}</span>.
              The intent enricher re-runs immediately — funding / hiring /
              competitor-tool keywords each push the buying-intent score up.
            </p>

            <div>
              <div className="text-[11px] uppercase tracking-wide text-textMuted mb-1.5">
                Quick templates
              </div>
              <div className="flex flex-wrap gap-2">
                {TEMPLATES.map((t) => (
                  <button
                    key={t.label}
                    onClick={() => chooseTemplate(t)}
                    disabled={submitting}
                    className="text-xs px-2.5 py-1 rounded-md border border-border bg-surface2 hover:border-accent hover:text-accent flex items-center gap-1"
                  >
                    <Sparkles className="w-3 h-3" />
                    {t.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-xs text-textMuted block mb-1">
                Headline
              </label>
              <input
                value={headline}
                onChange={(e) => setHeadline(e.target.value)}
                placeholder={`${co} announces $40M Series B`}
                disabled={submitting}
                className="w-full bg-surface2 border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-accent"
              />
            </div>

            <div>
              <label className="text-xs text-textMuted block mb-1">
                Source
              </label>
              <input
                value={source}
                onChange={(e) => setSource(e.target.value)}
                placeholder="TechCrunch"
                disabled={submitting}
                className="w-full bg-surface2 border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-accent"
              />
            </div>

            {error && <div className="text-xs text-danger">{error}</div>}

            <div className="flex justify-end gap-2 pt-1">
              <button
                onClick={() => setOpen(false)}
                disabled={submitting}
                className="btn-ghost text-xs px-3 py-1"
              >
                Cancel
              </button>
              <button
                onClick={submit}
                disabled={submitting}
                className="btn-primary text-xs px-3 py-1 flex items-center gap-1.5"
              >
                {submitting ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Plus className="w-3.5 h-3.5" />
                )}
                {submitting ? "Saving..." : "Add news"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
