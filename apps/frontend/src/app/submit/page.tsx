"use client";

import Link from "next/link";
import { useState } from "react";
import { createSubmission } from "../../lib/submissions";
import type { SubmissionResult } from "../../types/api";

export default function SubmitPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<SubmissionResult>(null);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const res = await createSubmission({ files, description });
      setResult(res);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Submission failed";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 p-10">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-2xl font-black tracking-tight">Submit a report</h1>
          <Link
            href="/"
            className="text-sm font-bold text-slate-600 hover:text-slate-900"
          >
            ← Back to dashboard
          </Link>
        </div>

        <form
          onSubmit={onSubmit}
          className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 space-y-5"
        >
          <div className="space-y-2">
            <label className="block text-xs font-black uppercase tracking-widest text-slate-400">
              Description (optional)
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full min-h-28 rounded-lg border border-slate-200 p-3 text-sm"
              placeholder="What happened? Where?"
            />
          </div>

          <div className="space-y-2">
            <label className="block text-xs font-black uppercase tracking-widest text-slate-400">
              Photos (optional)
            </label>
            <input
              type="file"
              multiple
              accept="image/png,image/jpeg,image/webp"
              onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
              className="block w-full text-sm"
            />
            <div className="text-xs text-slate-400">
              Selected: <span className="font-mono">{files.length}</span>
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="bg-blue-500 text-white px-5 py-2 rounded-lg font-bold text-xs hover:bg-blue-600 disabled:opacity-60"
          >
            {submitting ? "Submitting..." : "Submit"}
          </button>

          {error && (
            <div className="text-sm text-red-600 font-semibold">{error}</div>
          )}

          {result && (
            <div className="text-sm">
              <div className="font-bold mb-2">Result</div>
              <pre className="bg-slate-50 border border-slate-200 rounded-lg p-3 overflow-auto text-xs">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}

