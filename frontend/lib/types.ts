export type LeadState =
  | "new" | "enriched" | "contacted" | "engaged"
  | "replied" | "converted" | "cold" | "unsubscribed" | "closed";

export type DecisionType =
  | "send_email" | "send_linkedin_dm" | "suggest_call"
  | "wait" | "escalate_to_human" | "close_sequence";

export interface Company {
  id: string;
  name: string;
  domain?: string;
  industry?: string;
  employee_count?: number;
  employee_range?: string;
  location?: string;
  funding_stage?: string;
  tech_stack?: string[];
  recent_news?: NewsItem[];
  intent_score: number;
  icp_fit_score: number;
}

export interface NewsItem {
  headline: string;
  source?: string;
  url?: string;
  published_at?: string;
  summary?: string;
}

export interface Lead {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  job_title?: string;
  seniority_level?: string;
  linkedin_url?: string;
  phone?: string;
  source?: string;
  enrichment_status: string;
  enrichment_score: number;
  state: LeadState;
  state_updated_at?: string;
  next_action_at?: string;
  current_step: number;
  opted_out: boolean;
  created_at: string;
  updated_at: string;
  company?: Company;
  linkedin_signals?: any;
  company_news?: NewsItem[];
  tech_stack?: string[];
  intent_signals?: any;
}

export interface AgentDecision {
  id: string;
  lead_id: string;
  decision_type: DecisionType;
  channel_selected?: string;
  confidence_score: number;
  reasoning_summary: string;
  full_reasoning?: {
    signal_analysis?: string;
    situation_assessment?: string;
    options_considered?: string[];
    decision?: string;
    confidence?: number;
    reasoning_summary?: string;
    next_wait_days?: number;
    email_personalisation_hooks?: string[];
  };
  signals_observed?: any;
  lead_state_at_decision?: string;
  was_approved?: boolean | null;
  approved_by?: string;
  executed_at?: string;
  created_at: string;
}

export interface OverviewKPIs {
  total_active_leads: number;
  total_active_leads_delta: number;
  reply_rate_week: number;
  reply_rate_delta: number;
  emails_sent_today: number;
  decisions_made_today: number;
}

export interface WeeklyReplyRate {
  week_label: string;
  week_start: string;
  sent: number;
  replied: number;
  reply_rate: number;
}

export interface FunnelMetrics {
  sent: number;
  delivered: number;
  opened: number;
  clicked: number;
  replied: number;
}
