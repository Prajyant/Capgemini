"use client";

import { Bell, Search } from "lucide-react";

export function Navbar() {
  return (
    <header className="h-14 border-b border-border bg-surface/50 backdrop-blur flex items-center px-6 sticky top-0 z-10">
      <div className="flex-1 flex items-center gap-3">
        <div className="relative max-w-md w-full">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-textMuted" />
          <input
            type="text"
            placeholder="Search leads, decisions..."
            className="w-full bg-surface2 border border-border rounded-md pl-9 pr-3 py-1.5 text-sm placeholder:text-textMuted focus:outline-none focus:border-accent"
          />
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 px-3 py-1 bg-success/15 text-success rounded-md text-xs font-medium">
          <span className="w-2 h-2 bg-success rounded-full animate-pulse" />
          Agent Active
        </div>
        <button className="p-2 hover:bg-surface2 rounded-md text-textMuted hover:text-textPrimary">
          <Bell className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}
