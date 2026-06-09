"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import {
  AlertCircle,
  ChevronRight,
  Clock,
  Eye,
  Loader2,
  Mail,
  Plus,
  RefreshCw,
  Trash2,
  Workflow,
  X,
} from "lucide-react";

type Step = {
  id?: string;
  step_number: number;
  channel: string;
  subject_template?: string | null;
  body_template?: string | null;
  wait_days: number;
};

type Sequence = {
  id: string;
  name: string;
  vertical?: string | null;
  total_steps: number;
  is_active: boolean;
  created_at: string;
  steps: Step[];
};

type Email = {
  subject: string;
  body: string;
  personalisation_used?: string;
  spam_score: number;
  passes_spam_check: boolean;
  ab_variant: string;
};

const DEFAULT_STEPS: Step[] = [
  {
    step_number: 1,
    channel: "email",
    subject_template: "Quick thought, {first_name}",
    wait_days: 0,
  },
  {
    step_number: 2,
    channel: "email",
    subject_template: "Following up on {company_name}",
    wait_days: 3,
  },
  {
    step_number: 3,
    channel: "email",
    subject_template: "Last note from me",
    wait_days: 5,
  },
];

export default function SequencesPage() {
  const [seqs, setSeqs] = useState<Sequence[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [previewSeq, setPreviewSeq] = useState<Sequence | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listSequences();
      setSeqs(data || []);
    } catch (e: any) {
      setError(e?.message || "Failed to load sequences");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold mb-1">Sequences</h1>
          <p className="text-sm text-textMuted max-w-2xl">
            A sequence is a multi-touch outreach plan — an ordered list of steps
            (channel, wait days, optional subject hint) the agent uses as
            scaffolding. The actual subject and body of every email are generated
            per-lead at runtime from their enrichment context, so no two leads get
            the same copy.
          </p>
        </div>
        <button
          className="btn-primary flex items-center gap-2 shrink-0"
          onClick={() => setShowCreate(true)}
        >
          <Plus className="w-4 h-4" />
          New Sequence
        </button>
      </div>

      {loading && (
        <div className="card flex items-center gap-2 text-textMuted">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading sequences...
        </div>
      )}

      {error && !loading && (
        <div className="card flex items-center justify-between border-danger/40 bg-danger/10">
          <div className="flex items-center gap-2 text-danger">
            <AlertCircle className="w-4 h-4" />
            <span className="text-sm">{error}</span>
          </div>
          <button className="btn-ghost flex items-center gap-2" onClick={load}>
            <RefreshCw className="w-4 h-4" /> Retry
          </button>
        </div>
      )}

      {!loading && !error && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {seqs.map((s) => (
            <SequenceCard
              key={s.id}
              seq={s}
              onPreview={() => setPreviewSeq(s)}
            />
          ))}
          {seqs.length === 0 && (
            <div className="card text-center text-textMuted py-12 col-span-2">
              No sequences yet. Click <strong>New Sequence</strong> to create one.
            </div>
          )}
        </div>
      )}

      {showCreate && (
        <CreateSequenceModal
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            load();
          }}
        />
      )}

      {previewSeq && (
        <PreviewEmailsModal
          sequence={previewSeq}
          onClose={() => setPreviewSeq(null)}
        />
      )}
    </div>
  );
}

function SequenceCard({
  seq,
  onPreview,
}: {
  seq: Sequence;
  onPreview: () => void;
}) {
  return (
    <div className="card card-hover">
      <div className="flex items-start gap-3">
        <div className="p-2 bg-accent/15 rounded-md text-accent">
          <Workflow className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <div className="font-semibold truncate">{seq.name}</div>
            <button
              className="btn-ghost flex items-center gap-1.5 text-xs py-1 px-2"
              onClick={onPreview}
            >
              <Eye className="w-3.5 h-3.5" />
              Preview emails
            </button>
          </div>
          <div className="text-xs text-textMuted mt-0.5">
            {seq.vertical || "All verticals"} · {seq.total_steps} steps
          </div>

          <ol className="mt-3 space-y-2">
            {(seq.steps || []).map((step) => (
              <li
                key={step.id ?? step.step_number}
                className="flex items-start gap-2 text-xs"
              >
                <span className="badge bg-surface2 border border-border shrink-0">
                  Step {step.step_number}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 text-textPrimary">
                    <Mail className="w-3 h-3 text-textMuted" />
                    <span className="capitalize">{step.channel}</span>
                    <Clock className="w-3 h-3 text-textMuted ml-1" />
                    <span className="text-textMuted">
                      {step.wait_days === 0
                        ? "Day 0 (immediate)"
                        : `+${step.wait_days} days`}
                    </span>
                  </div>
                  {step.subject_template && (
                    <div className="text-textMuted italic truncate">
                      {step.subject_template}
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}

function CreateSequenceModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState("");
  const [vertical, setVertical] = useState("");
  const [steps, setSteps] = useState<Step[]>(DEFAULT_STEPS);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function updateStep(idx: number, patch: Partial<Step>) {
    setSteps((cur) => cur.map((s, i) => (i === idx ? { ...s, ...patch } : s)));
  }

  function addStep() {
    setSteps((cur) => [
      ...cur,
      {
        step_number: cur.length + 1,
        channel: "email",
        subject_template: "",
        wait_days: 3,
      },
    ]);
  }

  function removeStep(idx: number) {
    setSteps((cur) =>
      cur
        .filter((_, i) => i !== idx)
        .map((s, i) => ({ ...s, step_number: i + 1 }))
    );
  }

  async function submit() {
    if (!name.trim()) {
      setError("Name is required");
      return;
    }
    if (steps.length === 0) {
      setError("At least one step is required");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.createSequence({
        name: name.trim(),
        vertical: vertical.trim() || null,
        total_steps: steps.length,
        steps: steps.map((s, i) => ({
          step_number: i + 1,
          channel: s.channel || "email",
          subject_template: s.subject_template || null,
          body_template: s.body_template || null,
          wait_days: Number(s.wait_days) || 0,
        })),
      });
      onCreated();
    } catch (e: any) {
      setError(e?.message || "Failed to create sequence");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal title="New Sequence" onClose={onClose}>
      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <Field label="Name">
            <input
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. SaaS founders Q3 push"
              disabled={submitting}
            />
          </Field>
          <Field label="Vertical (optional)">
            <input
              className="input"
              value={vertical}
              onChange={(e) => setVertical(e.target.value)}
              placeholder="e.g. SaaS, Fintech"
              disabled={submitting}
            />
          </Field>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium">Steps</label>
            <button
              className="btn-ghost text-xs py-1 px-2"
              onClick={addStep}
              disabled={submitting}
            >
              + Add step
            </button>
          </div>
          <div className="space-y-2">
            {steps.map((s, idx) => (
              <div
                key={idx}
                className="bg-surface2 border border-border rounded-md p-3 space-y-2"
              >
                <div className="flex items-center justify-between">
                  <div className="font-medium text-sm">Step {idx + 1}</div>
                  {steps.length > 1 && (
                    <button
                      className="text-textMuted hover:text-danger"
                      onClick={() => removeStep(idx)}
                      aria-label="Remove step"
                      disabled={submitting}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                  <Field label="Channel">
                    <select
                      className="input"
                      value={s.channel}
                      onChange={(e) =>
                        updateStep(idx, { channel: e.target.value })
                      }
                      disabled={submitting}
                    >
                      <option value="email">Email</option>
                      <option value="linkedin">LinkedIn</option>
                    </select>
                  </Field>
                  <Field label="Wait (days)">
                    <input
                      type="number"
                      min={0}
                      className="input"
                      value={s.wait_days}
                      onChange={(e) =>
                        updateStep(idx, { wait_days: Number(e.target.value) })
                      }
                      disabled={submitting}
                    />
                  </Field>
                  <Field label="Subject hint">
                    <input
                      className="input"
                      value={s.subject_template || ""}
                      onChange={(e) =>
                        updateStep(idx, { subject_template: e.target.value })
                      }
                      placeholder="Quick thought, {first_name}"
                      disabled={submitting}
                    />
                  </Field>
                </div>
              </div>
            ))}
          </div>
        </div>

        {error && <div className="text-danger text-sm">{error}</div>}

        <div className="flex justify-end gap-2 pt-2">
          <button
            className="btn-ghost"
            onClick={onClose}
            disabled={submitting}
          >
            Cancel
          </button>
          <button
            className="btn-primary flex items-center gap-2"
            onClick={submit}
            disabled={submitting}
          >
            {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
            Create
          </button>
        </div>
      </div>
    </Modal>
  );
}

function PreviewEmailsModal({
  sequence,
  onClose,
}: {
  sequence: Sequence;
  onClose: () => void;
}) {
  const [leads, setLeads] = useState<any[]>([]);
  const [leadId, setLeadId] = useState<string>("");
  const [loadingLeads, setLoadingLeads] = useState(true);
  const [emails, setEmails] = useState<Email[] | null>(null);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .listLeads({ limit: 50 })
      .then((data) => {
        if (cancelled) return;
        setLeads(data || []);
        if (data && data.length > 0) setLeadId(data[0].id);
      })
      .catch((e) => {
        if (!cancelled) setError(e?.message || "Failed to load leads");
      })
      .finally(() => {
        if (!cancelled) setLoadingLeads(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function generate() {
    if (!leadId) return;
    setGenerating(true);
    setError(null);
    setEmails(null);
    try {
      const res = await api.getEmailsForLead(sequence.id, leadId);
      setEmails(res.emails || []);
    } catch (e: any) {
      setError(e?.message || "Failed to generate preview");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <Modal title={`Preview: ${sequence.name}`} onClose={onClose} wide>
      <div className="space-y-4">
        <p className="text-sm text-textMuted">
          Pick a lead — the agent will generate the personalised emails this
          sequence would produce using that lead's enrichment context. This calls
          the LLM, so it can take a few seconds.
        </p>

        <div className="flex items-end gap-2">
          <Field label="Lead" className="flex-1">
            {loadingLeads ? (
              <div className="text-textMuted text-sm">Loading leads...</div>
            ) : leads.length === 0 ? (
              <div className="text-textMuted text-sm">
                No leads available — import some from the Leads page first.
              </div>
            ) : (
              <select
                className="input"
                value={leadId}
                onChange={(e) => setLeadId(e.target.value)}
                disabled={generating}
              >
                {leads.map((l) => {
                  const fullName = `${l.first_name || ""} ${l.last_name || ""}`.trim();
                  const label = fullName || l.email;
                  const company = l.company?.name ? ` · ${l.company.name}` : "";
                  return (
                    <option key={l.id} value={l.id}>
                      {label}
                      {company}
                    </option>
                  );
                })}
              </select>
            )}
          </Field>
          <button
            className="btn-primary flex items-center gap-2"
            onClick={generate}
            disabled={generating || !leadId}
          >
            {generating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
            Generate
          </button>
        </div>

        {error && <div className="text-danger text-sm">{error}</div>}

        {emails && emails.length > 0 && (
          <div className="space-y-3 max-h-[55vh] overflow-y-auto pr-1">
            {emails.map((e, i) => (
              <div key={i} className="card">
                <div className="flex items-center justify-between mb-2 gap-2">
                  <div className="font-semibold truncate">
                    Step {i + 1}:{" "}
                    {e.subject || (
                      <span className="italic text-textMuted">(no subject)</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-xs shrink-0">
                    <span className="badge bg-surface2 border border-border">
                      Variant {e.ab_variant}
                    </span>
                    <span
                      className={`badge ${
                        e.passes_spam_check
                          ? "bg-success/15 text-success"
                          : "bg-danger/15 text-danger"
                      }`}
                    >
                      Spam {Number(e.spam_score ?? 0).toFixed(1)}
                    </span>
                  </div>
                </div>
                <pre className="text-sm text-textPrimary whitespace-pre-wrap font-sans">
                  {e.body}
                </pre>
                {e.personalisation_used && (
                  <div className="text-xs text-textMuted mt-2 border-t border-border pt-2">
                    Personalisation: {e.personalisation_used}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </Modal>
  );
}

function Modal({
  title,
  children,
  onClose,
  wide,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className={`bg-surface border border-border rounded-lg shadow-xl w-full ${
          wide ? "max-w-3xl" : "max-w-2xl"
        } max-h-[90vh] overflow-y-auto`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-border sticky top-0 bg-surface z-10">
          <h2 className="font-semibold">{title}</h2>
          <button
            className="text-textMuted hover:text-textPrimary"
            onClick={onClose}
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

function Field({
  label,
  children,
  className,
}: {
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <label className={`block ${className || ""}`}>
      <span className="block text-xs font-medium text-textMuted mb-1">
        {label}
      </span>
      {children}
    </label>
  );
}
