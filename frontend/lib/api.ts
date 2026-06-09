const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

export const api = {
  // Leads
  listLeads: (params: { state?: string; search?: string; limit?: number } = {}) => {
    const q = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])
    ).toString();
    return request<any[]>(`/api/leads${q ? `?${q}` : ""}`);
  },
  getLead: (id: string) => request<any>(`/api/leads/${id}`),
  updateLeadState: (id: string, state: string) =>
    request<any>(`/api/leads/${id}/state`, {
      method: "PUT",
      body: JSON.stringify({ state }),
    }),
  enrichLead: (id: string) =>
    request<any>(`/api/leads/${id}/enrich`, { method: "POST" }),

  simulateEngagement: (id: string, scenario: string) =>
    request<any>(`/api/leads/${id}/simulate-engagement?scenario=${scenario}`, { method: "POST" }),

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
  approveDecision: (id: string) =>
    request<any>(`/api/agent/decisions/${id}/approve`, { method: "POST" }),
  overrideDecision: (id: string, action: string) =>
    request<any>(`/api/agent/decisions/${id}/override?new_action=${action}`, {
      method: "POST",
    }),
  reasoningHistory: (leadId: string) =>
    request<any[]>(`/api/agent/reasoning/${leadId}`),

  // Sequences
  listSequences: () => request<any[]>("/api/sequences"),
  getEmailsForLead: (sequenceId: string, leadId: string) =>
    request<any>(`/api/sequences/${sequenceId}/emails/${leadId}`),

  // CRM
  crmStatus: () => request<{ hubspot: { connected: boolean; status: string }; salesforce: { connected: boolean; status: string } }>("/api/crm/status"),
  crmDisconnect: (crm: "hubspot" | "salesforce") =>
    request<{ status: string; crm: string }>(`/api/crm/${crm}/disconnect`, { method: "DELETE" }),

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
};

export const SSE_URL = `${BASE}/api/stream/activity`;
export const BACKEND_URL = BASE;

