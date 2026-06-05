"use client";

import { useState, useRef } from "react";
import { Upload, FileText, Check, X } from "lucide-react";
import { api } from "@/lib/api";

export function CSVUploader() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);

  const handleFile = (f: File | null) => {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".csv")) {
      alert("Please select a .csv file");
      return;
    }
    setFile(f);
    setResult(null);
  };

  const upload = async () => {
    if (!file) return;
    setUploading(true);
    try {
      const r = await api.importCsv(file);
      setResult(r);
    } catch (e: any) {
      setResult({ error: e.message });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          handleFile(e.dataTransfer.files[0] || null);
        }}
        onClick={() => inputRef.current?.click()}
        className={`card cursor-pointer flex flex-col items-center justify-center py-12 border-2 border-dashed transition ${
          drag ? "border-accent bg-accent/5" : "border-border"
        }`}
      >
        <Upload className="w-10 h-10 text-textMuted mb-3" />
        <div className="font-medium">
          {file ? file.name : "Drag & drop a CSV here, or click to select"}
        </div>
        <div className="text-xs text-textMuted mt-1">
          Required column: email · Optional: first_name, last_name, job_title, company_name, etc.
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0] || null)}
        />
      </div>

      {file && !result && (
        <div className="flex justify-end gap-2">
          <button onClick={() => setFile(null)} className="btn-ghost">
            Cancel
          </button>
          <button onClick={upload} disabled={uploading} className="btn-primary">
            {uploading ? "Importing..." : "Import & Enrich"}
          </button>
        </div>
      )}

      {result && (
        <div className="card">
          {result.error ? (
            <div className="text-danger flex items-center gap-2">
              <X className="w-4 h-4" />
              {result.error}
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2 text-success font-medium mb-2">
                <Check className="w-4 h-4" />
                Imported {result.imported} leads · {result.failed} skipped
              </div>
              <div className="text-xs text-textMuted">
                Enrichment is now running in the background. Open the Dashboard to watch.
              </div>
              {result.errors?.length > 0 && (
                <div className="mt-3 text-xs text-textMuted">
                  <div className="font-medium mb-1">Errors:</div>
                  <ul className="space-y-0.5">
                    {result.errors.slice(0, 5).map((e: any, i: number) => (
                      <li key={i}>Row {e.row}: {e.error}</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
