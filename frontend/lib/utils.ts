import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatRelative(dateStr?: string | null): string {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  const diff = Math.floor((Date.now() - d.getTime()) / 1000);
  
  // Future date
  if (diff < 0) {
    const absDiff = Math.abs(diff);
    if (absDiff < 60) return `in ${absDiff}s`;
    if (absDiff < 3600) return `in ${Math.floor(absDiff / 60)}m`;
    if (absDiff < 86400) return `in ${Math.floor(absDiff / 3600)}h`;
    return `in ${Math.floor(absDiff / 86400)}d`;
  }
  
  // Past date
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function formatPercent(v: number, digits = 1): string {
  return `${(v * 100).toFixed(digits)}%`;
}

export const STATE_COLORS: Record<string, string> = {
  new: "bg-slate-500/20 text-slate-300 border-slate-500/40",
  enriched: "bg-cyan-500/20 text-cyan-300 border-cyan-500/40",
  contacted: "bg-blue-500/20 text-blue-300 border-blue-500/40",
  engaged: "bg-purple-500/20 text-purple-300 border-purple-500/40",
  replied: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
  converted: "bg-success/20 text-success border-success/40",
  cold: "bg-warning/20 text-warning border-warning/40",
  unsubscribed: "bg-danger/20 text-danger border-danger/40",
  closed: "bg-slate-700 text-slate-400 border-slate-600",
};

export const DECISION_COLORS: Record<string, string> = {
  send_email: "bg-blue-500/20 text-blue-300 border-blue-500/40",
  send_linkedin_dm: "bg-cyan-500/20 text-cyan-300 border-cyan-500/40",
  suggest_call: "bg-purple-500/20 text-purple-300 border-purple-500/40",
  wait: "bg-warning/20 text-warning border-warning/40",
  escalate_to_human: "bg-danger/20 text-danger border-danger/40",
  close_sequence: "bg-slate-500/20 text-slate-300 border-slate-500/40",
};

export const DECISION_LABELS: Record<string, string> = {
  send_email: "Send Email",
  send_linkedin_dm: "LinkedIn DM",
  suggest_call: "Suggest Call",
  wait: "Wait",
  escalate_to_human: "Escalate",
  close_sequence: "Close",
};

export function leadDisplayName(lead?: {
  first_name?: string;
  last_name?: string;
  email?: string;
}): string {
  if (!lead) return "Unknown lead";
  const full = `${lead.first_name || ""} ${lead.last_name || ""}`.trim();
  return full || lead.email || "Unknown lead";
}
