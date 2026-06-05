"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Lead } from "@/lib/types";
import { StateBadge } from "@/components/shared/StatusBadge";
import { formatRelative } from "@/lib/utils";

export function LeadTable() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("");

  useEffect(() => {
    const load = async () => {
      try {
        const list = await api.listLeads({
          limit: 200,
          ...(filter ? { state: filter } : {}),
        });
        setLeads(list);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [filter]);

  const states = ["", "new", "enriched", "contacted", "engaged", "replied", "converted", "cold"];

  return (
    <div className="card overflow-hidden">
      <div className="flex items-center gap-2 mb-3">
        {states.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`text-xs px-3 py-1 rounded-md transition ${
              filter === s ? "bg-accent text-white" : "bg-surface2 text-textMuted hover:text-textPrimary"
            }`}
          >
            {s || "All"}
          </button>
        ))}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-textMuted border-b border-border">
              <th className="py-2 px-2">Name</th>
              <th className="py-2 px-2">Title</th>
              <th className="py-2 px-2">Company</th>
              <th className="py-2 px-2">State</th>
              <th className="py-2 px-2 text-right">Score</th>
              <th className="py-2 px-2">Updated</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={6} className="py-6 text-center text-textMuted">Loading...</td></tr>
            )}
            {!loading && leads.length === 0 && (
              <tr><td colSpan={6} className="py-6 text-center text-textMuted">No leads</td></tr>
            )}
            {leads.map((l) => (
              <tr key={l.id} className="border-b border-border/50 hover:bg-surface2/50">
                <td className="py-2 px-2">
                  <Link href={`/leads/${l.id}`} className="font-medium hover:text-accent">
                    {`${l.first_name || ""} ${l.last_name || ""}`.trim() || l.email}
                  </Link>
                  <div className="text-xs text-textMuted">{l.email}</div>
                </td>
                <td className="py-2 px-2 text-textMuted">{l.job_title || "—"}</td>
                <td className="py-2 px-2">{l.company?.name || "—"}</td>
                <td className="py-2 px-2"><StateBadge state={l.state} /></td>
                <td className="py-2 px-2 text-right tabular-nums font-medium">{l.enrichment_score}</td>
                <td className="py-2 px-2 text-xs text-textMuted">{formatRelative(l.updated_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
