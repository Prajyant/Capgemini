"use client";

import { Bell, Search, X, Brain, Check } from "lucide-react";
import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { DecisionBadge } from "@/components/shared/StatusBadge";
import { formatRelative } from "@/lib/utils";

interface SearchResult {
  id: string;
  name: string;
  email: string;
  company?: string;
  state: string;
}

export function Navbar() {
  const router = useRouter();

  // ── Search state ─────────────────────────────────────────────────────────
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const searchDebounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  const runSearch = useCallback(async (q: string) => {
    if (!q.trim()) { setResults([]); setSearchOpen(false); return; }
    setSearchLoading(true);
    setSearchOpen(true);
    try {
      const leads = await api.listLeads({ search: q, limit: 8 });
      setResults(leads.map((l: any) => ({
        id: l.id,
        name: [l.first_name, l.last_name].filter(Boolean).join(" ") || l.email,
        email: l.email,
        company: l.company?.name,
        state: l.state,
      })));
    } catch (e) {
      setResults([]);
    } finally {
      setSearchLoading(false);
    }
  }, []);

  useEffect(() => {
    if (searchDebounce.current) clearTimeout(searchDebounce.current);
    searchDebounce.current = setTimeout(() => runSearch(query), 300);
    return () => { if (searchDebounce.current) clearTimeout(searchDebounce.current); };
  }, [query, runSearch]);

  // Close search dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setSearchOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleSelect = (id: string) => {
    setQuery("");
    setResults([]);
    setSearchOpen(false);
    router.push(`/leads/${id}`);
  };

  // ── Notifications state ──────────────────────────────────────────────────
  const [notifOpen, setNotifOpen] = useState(false);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const notifRef = useRef<HTMLDivElement>(null);

  const loadNotifications = useCallback(async () => {
    try {
      const decisions = await api.listDecisions({ awaiting_approval: true, limit: 10 });
      setNotifications(decisions);
      setUnreadCount(decisions.length);
    } catch (e) {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadNotifications();
    const interval = setInterval(loadNotifications, 15000);
    return () => clearInterval(interval);
  }, [loadNotifications]);

  // Close notifications dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleApprove = async (id: string) => {
    try {
      await api.approveDecision(id);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch (e) { console.error(e); }
  };

  const handleOverride = async (id: string) => {
    try {
      await api.overrideDecision(id, "wait");
      setNotifications((prev) => prev.filter((n) => n.id !== id));
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch (e) { console.error(e); }
  };

  const STATE_DOT: Record<string, string> = {
    new: "bg-slate-400",
    enriched: "bg-cyan-400",
    contacted: "bg-blue-400",
    engaged: "bg-purple-400",
    replied: "bg-emerald-400",
    converted: "bg-green-400",
    cold: "bg-yellow-400",
    closed: "bg-slate-600",
  };

  return (
    <header className="h-14 border-b border-border bg-surface/50 backdrop-blur flex items-center px-6 sticky top-0 z-10">
      {/* Search */}
      <div className="flex-1 flex items-center gap-3">
        <div className="relative max-w-md w-full" ref={searchRef}>
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-textMuted pointer-events-none" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => query && setSearchOpen(true)}
            placeholder="Search leads by name, email, company..."
            className="w-full bg-surface2 border border-border rounded-md pl-9 pr-8 py-1.5 text-sm placeholder:text-textMuted focus:outline-none focus:border-accent"
          />
          {query && (
            <button
              onClick={() => { setQuery(""); setResults([]); setSearchOpen(false); }}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-textMuted hover:text-textPrimary"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}

          {/* Dropdown results */}
          {searchOpen && (
            <div className="absolute top-full mt-1 w-full bg-surface border border-border rounded-lg shadow-xl z-50 overflow-hidden">
              {searchLoading && (
                <div className="px-4 py-3 text-xs text-textMuted">Searching...</div>
              )}
              {!searchLoading && results.length === 0 && query && (
                <div className="px-4 py-3 text-xs text-textMuted">No leads found for "{query}"</div>
              )}
              {results.map((r) => (
                <button
                  key={r.id}
                  onClick={() => handleSelect(r.id)}
                  className="w-full text-left px-4 py-2.5 hover:bg-surface2 flex items-center gap-3 transition-colors border-b border-border/50 last:border-0"
                >
                  <span className={`w-2 h-2 rounded-full shrink-0 ${STATE_DOT[r.state] || "bg-slate-400"}`} />
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium truncate">{r.name}</div>
                    <div className="text-xs text-textMuted truncate">
                      {r.email}{r.company ? ` · ${r.company}` : ""}
                    </div>
                  </div>
                  <span className="text-[10px] text-textMuted capitalize shrink-0">{r.state}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Agent status pill */}
        <div className="flex items-center gap-2 px-3 py-1 bg-success/15 text-success rounded-md text-xs font-medium">
          <span className="w-2 h-2 bg-success rounded-full animate-pulse" />
          Agent Active
        </div>

        {/* Notification bell */}
        <div className="relative" ref={notifRef}>
          <button
            onClick={() => { setNotifOpen((o) => !o); if (!notifOpen) loadNotifications(); }}
            className="relative p-2 hover:bg-surface2 rounded-md text-textMuted hover:text-textPrimary transition-colors"
          >
            <Bell className="w-4 h-4" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 bg-danger text-white text-[9px] font-bold rounded-full flex items-center justify-center">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </button>

          {/* Notifications dropdown */}
          {notifOpen && (
            <div className="absolute right-0 top-full mt-1 w-96 bg-surface border border-border rounded-lg shadow-xl z-50 overflow-hidden">
              <div className="px-4 py-3 border-b border-border flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Brain className="w-4 h-4 text-accent" />
                  <span className="font-semibold text-sm">Pending Decisions</span>
                </div>
                {unreadCount > 0 && (
                  <span className="badge bg-danger/20 text-danger border border-danger/30 text-[10px]">
                    {unreadCount} awaiting review
                  </span>
                )}
              </div>

              <div className="max-h-[420px] overflow-y-auto divide-y divide-border/50">
                {notifications.length === 0 && (
                  <div className="px-4 py-6 text-center text-xs text-textMuted">
                    <Check className="w-5 h-5 mx-auto mb-2 text-success" />
                    All caught up — no pending decisions
                  </div>
                )}
                {notifications.map((n) => (
                  <div key={n.id} className="px-4 py-3 hover:bg-surface2/50 transition-colors">
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <DecisionBadge decision={n.decision_type} />
                      <span className="text-[10px] text-textMuted shrink-0">
                        {formatRelative(n.created_at)}
                      </span>
                    </div>
                    <p className="text-xs text-textMuted leading-relaxed mb-2 line-clamp-2">
                      {n.reasoning_summary}
                    </p>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleApprove(n.id)}
                        className="flex-1 flex items-center justify-center gap-1 py-1 rounded-md bg-success/15 text-success hover:bg-success/25 text-xs font-medium transition-colors"
                      >
                        <Check className="w-3 h-3" />
                        Approve
                      </button>
                      <button
                        onClick={() => handleOverride(n.id)}
                        className="flex-1 flex items-center justify-center gap-1 py-1 rounded-md bg-surface2 border border-border text-textMuted hover:text-textPrimary text-xs font-medium transition-colors"
                      >
                        <X className="w-3 h-3" />
                        Override
                      </button>
                      <button
                        onClick={() => { router.push(`/leads/${n.lead_id}`); setNotifOpen(false); }}
                        className="px-2 py-1 rounded-md bg-accent/10 text-accent hover:bg-accent/20 text-xs font-medium transition-colors"
                      >
                        View
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {notifications.length > 0 && (
                <div className="px-4 py-2 border-t border-border">
                  <button
                    onClick={() => { router.push("/agent-feed"); setNotifOpen(false); }}
                    className="w-full text-xs text-accent hover:underline text-center"
                  >
                    View all in Agent Feed →
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
