"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Bell,
  Brain,
  CheckCheck,
  Mail,
  MessageSquare,
  Search,
  Sparkles,
  Megaphone,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import {
  getDemoRecipient,
  setDemoRecipient,
  onDemoRecipientChange,
} from "@/lib/demoMode";
import { formatRelative } from "@/lib/utils";

const LAST_READ_KEY = "notifications:last_read_at";

type Activity = {
  type: string;
  lead_id?: string;
  lead_name?: string;
  decision?: string;
  confidence?: number;
  summary?: string;
  event?: string;
  sentiment?: string;
  intent?: string;
  score?: number;
  timestamp: string;
};

export function Navbar() {
  return (
    <header className="h-14 border-b border-border bg-surface/50 backdrop-blur flex items-center px-6 sticky top-0 z-20">
      <div className="flex-1 flex items-center gap-3">
        <SearchBox />
      </div>
      <div className="flex items-center gap-3">
        <DemoRecipientWidget />
        <div className="flex items-center gap-2 px-3 py-1 bg-success/15 text-success rounded-md text-xs font-medium">
          <span className="w-2 h-2 bg-success rounded-full animate-pulse" />
          Agent Active
        </div>
        <NotificationsBell />
      </div>
    </header>
  );
}

/* ───────────────────  DEMO RECIPIENT OVERRIDE  ──────────────────── */

/**
 * Lets the presenter route every outgoing email — Compose Email, Approve,
 * sequence step send — to their own inbox during a live demo. The value
 * is persisted in localStorage so it survives reloads, and a custom
 * window event keeps every component in sync without prop drilling.
 */
function DemoRecipientWidget() {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");
  const [draft, setDraft] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  // Hydrate from localStorage and listen for changes (e.g. another tab).
  useEffect(() => {
    setValue(getDemoRecipient());
    const off = onDemoRecipientChange(() => setValue(getDemoRecipient()));
    return off;
  }, []);

  useEffect(() => {
    if (open) setDraft(value);
  }, [open, value]);

  // Outside-click / Esc closes the popover.
  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (!containerRef.current) return;
      if (!containerRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const active = value.trim().length > 0;

  function save() {
    setDemoRecipient(draft);
    setOpen(false);
  }

  function clear() {
    setDemoRecipient("");
    setOpen(false);
  }

  return (
    <div className="relative" ref={containerRef}>
      <button
        onClick={() => setOpen((v) => !v)}
        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border transition ${
          active
            ? "bg-warning/15 text-warning border-warning/40"
            : "bg-surface2 text-textMuted border-border hover:text-textPrimary"
        }`}
        title={
          active
            ? `All sends are being redirected to ${value}`
            : "Set a demo recipient to redirect every send"
        }
      >
        <Megaphone className="w-3.5 h-3.5" />
        {active ? `Demo → ${value}` : "Demo recipient"}
      </button>

      {open && (
        <div className="absolute right-0 mt-1.5 w-80 bg-surface border border-border rounded-md shadow-xl p-3 z-30 space-y-2">
          <div className="text-sm font-semibold flex items-center justify-between">
            <span>Demo recipient override</span>
            <button
              className="text-textMuted hover:text-textPrimary"
              onClick={() => setOpen(false)}
              aria-label="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <p className="text-xs text-textMuted leading-relaxed">
            When set, every Compose Email / Approve / Send Step will deliver
            to this address instead of the lead's real email. The lead's
            timeline still records the event normally.
          </p>
          <input
            type="email"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="you@example.com"
            className="w-full bg-surface2 border border-border rounded-md px-3 py-1.5 text-sm focus:outline-none focus:border-accent"
            autoFocus
          />
          <div className="flex justify-between gap-2 pt-1">
            <button
              onClick={clear}
              className="btn-ghost text-xs px-3 py-1"
              disabled={!active && !draft}
            >
              Clear
            </button>
            <button onClick={save} className="btn-primary text-xs px-3 py-1">
              Save
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/* ─────────────────────────────  SEARCH  ───────────────────────────── */

function SearchBox() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [activeIdx, setActiveIdx] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reqIdRef = useRef(0);

  // Debounced search
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const q = query.trim();
    if (!q) {
      setResults([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    const myReq = ++reqIdRef.current;
    debounceRef.current = setTimeout(async () => {
      try {
        const list = await api.listLeads({ search: q, limit: 8 });
        // Ignore if a newer request started after this one
        if (myReq !== reqIdRef.current) return;
        setResults(list || []);
        setActiveIdx(0);
      } catch (e) {
        if (myReq !== reqIdRef.current) return;
        setResults([]);
      } finally {
        if (myReq === reqIdRef.current) setLoading(false);
      }
    }, 250);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  // Close on outside click
  useEffect(() => {
    function onDown(e: MouseEvent) {
      if (!containerRef.current) return;
      if (!containerRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, []);

  function go(leadId: string) {
    setOpen(false);
    setQuery("");
    setResults([]);
    router.push(`/leads/${leadId}`);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Escape") {
      setOpen(false);
      (e.target as HTMLInputElement).blur();
      return;
    }
    if (!open || results.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const target = results[activeIdx];
      if (target) go(target.id);
    }
  }

  const showDropdown = open && query.trim().length > 0;

  return (
    <div className="relative max-w-md w-full" ref={containerRef}>
      <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-textMuted pointer-events-none" />
      <input
        type="text"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        placeholder="Search leads by name, email, company..."
        className="w-full bg-surface2 border border-border rounded-md pl-9 pr-3 py-1.5 text-sm placeholder:text-textMuted focus:outline-none focus:border-accent"
        autoComplete="off"
      />

      {showDropdown && (
        <div className="absolute left-0 right-0 mt-1.5 bg-surface border border-border rounded-md shadow-xl overflow-hidden z-30">
          {loading && (
            <div className="px-3 py-3 text-xs text-textMuted">Searching...</div>
          )}
          {!loading && results.length === 0 && (
            <div className="px-3 py-3 text-xs text-textMuted">
              No matches for &ldquo;{query.trim()}&rdquo;.
            </div>
          )}
          {!loading && results.length > 0 && (
            <ul className="max-h-80 overflow-y-auto">
              {results.map((l, i) => {
                const name =
                  `${l.first_name || ""} ${l.last_name || ""}`.trim() ||
                  l.email;
                return (
                  <li key={l.id}>
                    <button
                      onMouseEnter={() => setActiveIdx(i)}
                      onClick={() => go(l.id)}
                      className={`w-full text-left px-3 py-2 text-sm flex items-center gap-3 ${
                        i === activeIdx ? "bg-surface2" : "hover:bg-surface2/60"
                      }`}
                    >
                      <div className="w-7 h-7 rounded-full bg-accent/15 text-accent text-xs flex items-center justify-center shrink-0 font-semibold">
                        {(name[0] || "?").toUpperCase()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="truncate text-textPrimary">{name}</div>
                        <div className="text-xs text-textMuted truncate">
                          {l.job_title ? `${l.job_title} · ` : ""}
                          {l.company?.name || l.email}
                        </div>
                      </div>
                      <span className="badge bg-surface2 border border-border capitalize text-textMuted">
                        {l.state}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

/* ───────────────────────  NOTIFICATIONS BELL  ────────────────────── */

function NotificationsBell() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(false);
  const [lastReadAt, setLastReadAt] = useState<string>("");
  const containerRef = useRef<HTMLDivElement>(null);

  // Load last-read pointer from localStorage
  useEffect(() => {
    if (typeof window === "undefined") return;
    setLastReadAt(window.localStorage.getItem(LAST_READ_KEY) || "");
  }, []);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.activityFeed(30);
      setItems(Array.isArray(data) ? data : []);
    } catch {
      // Stay quiet — bell shouldn't yell when backend is down
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load + slow background refresh (every 60s).
  useEffect(() => {
    load();
    const id = setInterval(load, 60000);
    return () => clearInterval(id);
  }, [load]);

  // Refresh on open and mark as read
  useEffect(() => {
    if (!open) return;
    load();
    const now = new Date().toISOString();
    setLastReadAt(now);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(LAST_READ_KEY, now);
    }
  }, [open, load]);

  // Outside click / Escape
  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (!containerRef.current) return;
      if (!containerRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const unreadCount = useMemo(() => {
    if (!lastReadAt) return Math.min(items.length, 9);
    const cutoff = Date.parse(lastReadAt);
    if (isNaN(cutoff)) return 0;
    return items.filter((i) => {
      const t = Date.parse(i.timestamp || "");
      return !isNaN(t) && t > cutoff;
    }).length;
  }, [items, lastReadAt]);

  function markAllRead() {
    const now = new Date().toISOString();
    setLastReadAt(now);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(LAST_READ_KEY, now);
    }
  }

  return (
    <div className="relative" ref={containerRef}>
      <button
        className="p-2 hover:bg-surface2 rounded-md text-textMuted hover:text-textPrimary relative"
        onClick={() => setOpen((v) => !v)}
        aria-label="Notifications"
      >
        <Bell className="w-4 h-4" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-danger text-white text-[10px] font-semibold flex items-center justify-center">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-1.5 w-96 bg-surface border border-border rounded-md shadow-xl overflow-hidden z-30">
          <div className="flex items-center justify-between px-3 py-2 border-b border-border">
            <div className="font-semibold text-sm">Notifications</div>
            {items.length > 0 && (
              <button
                onClick={markAllRead}
                className="text-xs text-textMuted hover:text-textPrimary flex items-center gap-1"
              >
                <CheckCheck className="w-3.5 h-3.5" />
                Mark all read
              </button>
            )}
          </div>
          <div className="max-h-96 overflow-y-auto">
            {loading && items.length === 0 && (
              <div className="px-3 py-6 text-center text-xs text-textMuted">
                Loading...
              </div>
            )}
            {!loading && items.length === 0 && (
              <div className="px-3 py-8 text-center text-xs text-textMuted">
                Nothing new. Activity will show up here as the agent works.
              </div>
            )}
            <ul>
              {items.map((a, idx) => (
                <NotificationRow
                  key={`${a.type}-${a.timestamp}-${idx}`}
                  activity={a}
                  onNavigate={() => setOpen(false)}
                />
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

function NotificationRow({
  activity,
  onNavigate,
}: {
  activity: Activity;
  onNavigate: () => void;
}) {
  const meta = activityMeta(activity);
  const Icon = meta.Icon;

  const inner = (
    <div
      className={`flex gap-3 px-3 py-2.5 border-b border-border/50 ${
        activity.lead_id ? "hover:bg-surface2 cursor-pointer" : ""
      }`}
    >
      <div
        className={`w-8 h-8 rounded-md flex items-center justify-center shrink-0 ${meta.tint}`}
      >
        <Icon className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-xs text-textPrimary leading-snug">
          <span className="font-medium">{meta.title}</span>
          {meta.detail && (
            <span className="text-textMuted"> — {meta.detail}</span>
          )}
        </div>
        <div className="text-[10px] text-textMuted mt-0.5">
          {formatRelative(activity.timestamp)}
        </div>
      </div>
    </div>
  );

  if (activity.lead_id) {
    return (
      <li>
        <Link href={`/leads/${activity.lead_id}`} onClick={onNavigate}>
          {inner}
        </Link>
      </li>
    );
  }
  return <li>{inner}</li>;
}

function activityMeta(a: Activity) {
  const who = a.lead_name || "a lead";
  switch (a.type) {
    case "agent_decision":
      return {
        Icon: Brain,
        tint: "bg-accent/15 text-accent",
        title: `Agent: ${(a.decision || "decision").replace(/_/g, " ")}`,
        detail: `${who}${
          typeof a.confidence === "number"
            ? ` · ${(a.confidence * 100).toFixed(0)}%`
            : ""
        }${a.summary ? ` — ${truncate(a.summary, 80)}` : ""}`,
      };
    case "enrichment":
      return {
        Icon: Sparkles,
        tint: "bg-warning/15 text-warning",
        title: "Lead enriched",
        detail: `${who}${
          typeof a.score === "number" ? ` · score ${a.score}` : ""
        }`,
      };
    case "email_event":
      return {
        Icon: Mail,
        tint: "bg-success/15 text-success",
        title: `Email ${a.event || "event"}`,
        detail: who,
      };
    case "reply":
      return {
        Icon: MessageSquare,
        tint: "bg-accent/15 text-accent",
        title: "Reply received",
        detail: `${who}${a.intent ? ` · ${a.intent}` : ""}${
          a.sentiment ? ` (${a.sentiment})` : ""
        }`,
      };
    default:
      return {
        Icon: Bell,
        tint: "bg-surface2 text-textMuted",
        title: a.type || "Activity",
        detail: who,
      };
  }
}

function truncate(s: string, n: number) {
  if (!s) return s;
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}
