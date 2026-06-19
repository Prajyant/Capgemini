const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

import { getDemoRecipient } from "./demoMode";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${path} failed: ${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

/**
 * Inject the demo recipient override (if set) into a send payload.
 * The presenter's choice in the navbar wins unless the caller explicitly
 * passed a `to_email` already.
 */
function withDemoRecipient<T extends { to_email?: string }>(payload: T): T {
  if (payload.to_email) return payload;
  const override = getDemoRecipient();
  if (!override) return payload;
  return { ...payload, to_email: override };
}

export const api = {
  // Leads
  listLeads: (params: { state?: string; search?: string; limit?: number } = {}) => {
    const q = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])
    ).toString();
    return request<any[]>(`/api/leads${q ? `?${q}` : ""}`);
  },
  getLead: (id: string) => request<any>(`/api/leads/${id}`),
  getLeadEvents: (id: string) => request<any[]>(`/api/leads/${id}/events`),
  updateLeadState: (id: string, state: string) =>
    request<any>(`/api/leads/${id}/state`, {
      method: "PUT",
      body: JSON.stringify({ state }),
    }),
  enrichLead: (id: string) =>
    request<any>(`/api/leads/${id}/enrich`, { method: "POST" }),

  addLeadNews: (
    id: string,
    payload: { headline: string; source?: string; url?: string; summary?: string; published_at?: string }
  ) =>
    request<any>(`/api/leads/${id}/news`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  removeLeadNews: (id: string, index: number) =>
    request<any>(`/api/leads/${id}/news/${index}`, { method: "DELETE" }),

  simulateInboundReply: (payload: {
    from_email: string;
    subject?: string;
    body: string;
  }) =>
    request<any>("/api/webhooks/reply", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  checkInbox: () =>
    request<any>("/api/webhooks/check-inbox", { method: "POST" }),

  importCsv: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BASE}/api/leads/import/csv`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) throw new Error(`Import failed: ${res.status}`);
    return res.json();
  },

  seedDemoLeads: (wipe = true) =>
    request<{ wiped: boolean; created: number; lead_ids: string[] }>(
      `/api/leads/seed-demo?wipe=${wipe}`,
      { method: "POST" }
    ),

  // Agent
  decideForLead: (leadId: string) =>
    request<any>(`/api/agent/decide/${leadId}`, { method: "POST" }),
  decideBatch: (limit = 20) =>
    request<any>(`/api/agent/decide/batch?limit=${limit}`, { method: "POST" }),
  listDecisions: (params: Record<string, string | number | boolean> = {}) => {
    const q = new URLSearchParams(
      Object.entries(params).map(([k, v]) => [k, String(v)])
    ).toString();
    return request<any[]>(`/api/agent/decisions${q ? `?${q}` : ""}`);
  },
  approveDecision: (id: string, payload?: { to_email?: string }) => {
    const body = withDemoRecipient(payload || {});
    return request<any>(`/api/agent/decisions/${id}/approve`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  overrideDecision: (id: string, action: string) =>
    request<any>(`/api/agent/decisions/${id}/override?new_action=${action}`, {
      method: "POST",
    }),
  reasoningHistory: (leadId: string) =>
    request<any[]>(`/api/agent/reasoning/${leadId}`),
  draftEmail: (leadId: string) =>
    request<any>(`/api/agent/draft-email/${leadId}`, { method: "POST" }),
  sendEmail: (
    leadId: string,
    payload: { subject: string; body: string; to_email?: string }
  ) =>
    request<any>(`/api/agent/send-email/${leadId}`, {
      method: "POST",
      body: JSON.stringify(withDemoRecipient(payload)),
    }),

  // Sequences
  listSequences: () => request<any[]>("/api/sequences"),
  createSequence: (payload: {
    name: string;
    vertical?: string | null;
    total_steps: number;
    steps: Array<{
      step_number: number;
      channel: string;
      subject_template?: string | null;
      body_template?: string | null;
      wait_days: number;
    }>;
  }) =>
    request<any>("/api/sequences", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getEmailsForLead: (sequenceId: string, leadId: string) =>
    request<any>(`/api/sequences/${sequenceId}/emails/${leadId}`),
  sendSequenceStep: (
    leadId: string,
    payload: {
      sequence_id: string;
      step_number: number;
      subject: string;
      body: string;
      ab_variant?: string;
      to_email?: string;
    }
  ) =>
    request<any>(`/api/sequences/send-step/${leadId}`, {
      method: "POST",
      body: JSON.stringify(withDemoRecipient(payload)),
    }),
  enrollLeadInSequence: (sequenceId: string, leadId: string, startNow = true) =>
    request<any>(
      `/api/sequences/${sequenceId}/enroll/${leadId}?start_now=${startNow}`,
      { method: "POST" }
    ),
  progressSequencesNow: () =>
    request<any>("/api/sequences/progress/run-now", { method: "POST" }),

  // Analytics
  overview: () => request<any>("/api/analytics/overview"),
  weeklyReplyRate: (weeks = 8) =>
    request<any[]>(`/api/analytics/reply-rate?weeks=${weeks}`),
  funnel: () => request<any>("/api/analytics/funnel"),
  channels: () => request<any[]>("/api/analytics/channels"),
  abTests: () => request<any[]>("/api/analytics/ab-tests"),
  agentPerformance: () => request<any>("/api/analytics/agent-performance"),
  activityFeed: (limit = 30) =>
    request<any[]>(`/api/analytics/activity-feed?limit=${limit}`),

  // Settings
  settingsStatus: () => request<any>("/api/settings/status"),
};

export const SSE_URL = `${BASE}/api/stream/activity`;
