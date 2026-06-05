import { LeadTable } from "@/components/leads/LeadTable";
import Link from "next/link";
import { Upload } from "lucide-react";

export default function LeadsPage() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold mb-1">Leads</h1>
          <p className="text-sm text-textMuted">
            Filter, search, and dive into individual lead profiles.
          </p>
        </div>
        <Link href="/import" className="btn-primary flex items-center gap-2">
          <Upload className="w-4 h-4" />
          Import Leads
        </Link>
      </div>
      <LeadTable />
    </div>
  );
}
