"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Lead } from "@/lib/types";
import { StateBadge } from "@/components/shared/StatusBadge";
import { formatRelative } from "@/lib/utils";
import { ArrowUpDown, Brain, Search } from "lucide-react";

const STATES = ["", "new", "enriched", "contacted", "engaged", "replied", "converted", "cold", "closed"];

const STATE_LABELS: Record<string, string> = {
  "": "All",
  new: "New",
  enriched: "Enriched",
  contacted: "Contacted",
  engaged: "Engaged",
  replied: "Replied",
  converted: "Converted",
  cold: "Cold",
  closed: "Closed",
};

export function LeadTable() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("");
  const [search, setSearch] = useState<string>("");
  const [sortField, setSortField] = useState<"enrichment_score" | "updated_at" | "state">("updated_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const list = await api.listLeads({
          limit: 200,
          ...(filter ? { state: filter } : {}),
          ...(search ? { search } : {}),
        });
        setLeads(list);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [filter, search]);

  const toggleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("desc");
    }
  };

  const sorted = [...leads].sort((a, b) => {
    let av: any, bv: any;
    if (sortField === "enrichment_score") {
      av = a.enrichment_score;
      bv = b.enrichment_score;
    } else if (sortField === "updated_at") {
      av = new Date(a.updated_at).getTime();
      bv = new Date(b.updated_at).getTime();
    } else {
      av = a.state;
      bv = b.state;
    }
    if (av < bv) return sortDir === "asc" ? -1 : 1;
    if (av > bv) return sortDir === "asc" ? 1 : -1;
    return 0;
  });

  const SortButton = ({ field, label }: { field: typeof sortField; label: string }) => (
    <button
      onClick={() => toggleSort(field)}
      className="flex items-center gap-1 hover:text-textPrimary transition-colors"
    >
      {label}
      <ArrowUpDown className={`w-3 h-3 ${sortField === field ? "text-accent" : "text-textMuted/50"}`} />
    </button>
  );

  return (
    <div className="card overflow-hidden space-y-3">
      {/* Filters row */}
      <div className="flex flex-wrap items-center gap-2">
        {/* State filters */}
        <div className="flex flex-wrap gap-1.5">
          {STATES.map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`text-xs px-2.5 py-1 rounded-md font-medium transition-colors border ${
                filter === s
                  ? "bg-accent text-white border-accent"
                  : "bg-surface2 text-textMuted border-border hover:text-textPrimary hover:border-accent/30"
              }`}
            >
              {STATE_LABELS[s]}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="ml-auto relative">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-textMuted pointer-events-none" />
          <input
            type="text"
            placeholder="Search leads..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-surface2 border border-border rounded-md pl-8 pr-3 py-1 text-xs focus:outline-none focus:border-accent w-44"
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto -mx-4 px-4">
        <table className="w-full text-sm min-w-[700px]">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-textMuted border-b border-border">
              <th className="py-2.5 px-3 font-semibold">Name / Email</th>
              <th className="py-2.5 px-3 font-semibold">Role</th>
              <th className="py-2.5 px-3 font-semibold">Company</th>
              <th className="py-2.5 px-3 font-semibold">
                <SortButton field="state" label="Status" />
              </th>
              <th className="py-2.5 px-3 font-semibold text-right">
                <SortButton field="enrichment_score" label="Score" />
              </th>
              <th className="py-2.5 px-3 font-semibold">
                <SortButton field="updated_at" label="Last Updated" />
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/40">
            {loading && (
              <tr>
                <td colSpan={6} className="py-8 text-center text-textMuted text-sm">
                  <div className="flex items-center justify-center gap-2">
                    <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                    Loading leads...
                  </div>
                </td>
              </tr>
            )}
            {!loading && sorted.length === 0 && (
              <tr>
                <td colSpan={6} className="py-8 text-center text-textMuted text-sm">
                  {search || filter ? "No leads match your filters." : "No leads yet. Import a CSV to get started."}
                </td>
              </tr>
            )}
            {sorted.map((l) => {
              const fullName = `${l.first_name || ""} ${l.last_name || ""}`.trim();
              const initials = fullName
                .split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();
              return (
                <tr key={l.id} className="hover:bg-surface2/40 transition-colors group">
                  <td className="py-3 px-3">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-accent/20 text-accent text-xs font-bold flex items-center justify-center shrink-0">
                        {initials || "?"}
                      </div>
                      <div>
                        <Link
                          href={`/leads/${l.id}`}
                          className="font-semibold text-textPrimary hover:text-accent transition-colors block leading-tight"
                        >
                          {fullName || "—"}
                        </Link>
                        <span className="text-xs text-textMuted">{l.email}</span>
                      </div>
                    </div>
                  </td>
                  <td className="py-3 px-3">
                    <span className="text-sm text-textMuted">{l.job_title || "—"}</span>
                    {l.seniority_level && (
                      <span className="ml-1.5 text-[10px] badge bg-surface2 border border-border text-textMuted">
                        {l.seniority_level}
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-3">
                    <span className="text-sm text-textPrimary font-medium">
                      {l.company?.name || "—"}
                    </span>
                    {l.company?.industry && (
                      <div className="text-xs text-textMuted">{l.company.industry}</div>
                    )}
                  </td>
                  <td className="py-3 px-3">
                    <StateBadge state={l.state} />
                  </td>
                  <td className="py-3 px-3 text-right">
                    <div className="inline-flex flex-col items-end">
                      <span className="font-bold tabular-nums text-textPrimary">
                        {l.enrichment_score}
                        <span className="text-textMuted text-xs font-normal">/100</span>
                      </span>
                      {/* Mini bar */}
                      <div className="w-12 h-1 bg-surface2 rounded-full mt-1 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-accent"
                          style={{ width: `${l.enrichment_score}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="py-3 px-3 text-xs text-textMuted whitespace-nowrap">
                    {formatRelative(l.updated_at)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      {!loading && sorted.length > 0 && (
        <div className="text-xs text-textMuted pt-1">
          Showing {sorted.length} lead{sorted.length !== 1 ? "s" : ""}
          {filter ? ` in state "${STATE_LABELS[filter]}"` : ""}
          {search ? ` matching "${search}"` : ""}
        </div>
      )}
    </div>
  );
}
