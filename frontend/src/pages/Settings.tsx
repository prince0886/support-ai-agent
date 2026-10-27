import { useState, type FormEvent } from "react";
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Database,
  FlaskConical,
  KeyRound,
  RefreshCw,
  Search,
  Server,
  ShieldCheck,
  Sparkles,
  Terminal,
  XCircle,
  Zap,
} from "lucide-react";

import {
  EngineBadge,
  ErrorState,
  KeyValue,
  PageHeader,
  Spinner,
} from "../components/ui";
import { api, errorMessage } from "../lib/api";
import { formatDateTime } from "../lib/format";
import type { AITestResult, KnowledgeSearchResponse } from "../lib/types";
import { useApp } from "../store/AppStore";

function Step({
  index,
  title,
  description,
}: {
  index: number;
  title: string;
  description: string;
}) {
  return (
    <li className="flex gap-2.5">
      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-900 text-[10px] font-semibold text-white">
        {index}
      </span>
      <div>
        <p className="text-xs font-semibold text-slate-800">{title}</p>
        <p className="mt-0.5 text-[11px] leading-relaxed text-slate-500">{description}</p>
      </div>
    </li>
  );
}

export function SettingsPage() {
  const { status, metrics, refresh, toast } = useApp();
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<AITestResult | null>(null);
  const [testError, setTestError] = useState<string | null>(null);
  const [resetConfirm, setResetConfirm] = useState(false);
  const [resetting, setResetting] = useState(false);

  const [query, setQuery] = useState("refund window");
  const [searching, setSearching] = useState(false);
  const [hits, setHits] = useState<KnowledgeSearchResponse["hits"] | null>(null);

  if (!status) {
    return (
      <div>
        <PageHeader title="Settings" subtitle="AI provider, retrieval and demo controls." />
        <div className="card p-6">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Spinner /> Loading configuration…
          </div>
        </div>
      </div>
    );
  }

  const ai = status.ai;

  const testConnection = async () => {
    setTesting(true);
    setTestError(null);
    try {
      const result = await api.testAi();
      setTestResult(result);
      toast(
        result.ok ? "Model connection succeeded." : "Model unreachable — the fallback analyst is active.",
        result.ok ? "success" : "error",
      );
    } catch (cause) {
      setTestError(errorMessage(cause));
      toast(errorMessage(cause), "error");
    } finally {
      setTesting(false);
    }
  };

  const resetDemo = async () => {
    setResetting(true);
    try {
      const result = await api.resetDemo();
      await refresh();
      setResetConfirm(false);
      toast(`Demo data restored: ${result.tickets} tickets, ${result.articles} articles.`, "success");
    } catch (cause) {
      toast(errorMessage(cause), "error");
    } finally {
      setResetting(false);
    }
  };

  const runSearch = async (event: FormEvent) => {
    event.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    try {
      const result = await api.searchKnowledge(query.trim(), status.retrieval_top_k);
      setHits(result.hits);
    } catch (cause) {
      toast(errorMessage(cause), "error");
    } finally {
      setSearching(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="Settings"
        subtitle="How SupportPilot is wired, what is live, and what the demo simulates."
      >
        <span className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500">
          <Server className="h-3.5 w-3.5" /> {status.environment} environment
        </span>
      </PageHeader>

      <div className="grid gap-4 xl:grid-cols-3 xl:items-start">
        <section className="card p-5 xl:col-span-2">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                <Sparkles className="h-4 w-4" />
              </span>
              <div>
                <h2 className="text-sm font-semibold text-slate-900">AI engine</h2>
                <p className="text-[11px] text-slate-500">OpenAI-compatible provider, configured server-side.</p>
              </div>
            </div>
            <EngineBadge mode={ai.mode} />
          </div>

          <div
            className={`mt-4 flex items-start gap-2.5 rounded-lg border px-3.5 py-3 ${
              ai.mode === "llm"
                ? "border-brand-200 bg-brand-50/50"
                : "border-amber-200 bg-amber-50/60"
            }`}
          >
            {ai.mode === "llm" ? (
              <Zap className="mt-0.5 h-4 w-4 text-brand-600" />
            ) : (
              <ShieldCheck className="mt-0.5 h-4 w-4 text-amber-600" />
            )}
            <div className="text-xs leading-relaxed">
              <p className={`font-semibold ${ai.mode === "llm" ? "text-brand-900" : "text-amber-900"}`}>
                {ai.mode === "llm"
                  ? "Live model configured and responding"
                  : ai.degraded
                    ? "Provider unreachable — fallback active"
                    : "Deterministic fallback active"}
              </p>
              <p className={ai.mode === "llm" ? "text-brand-800" : "text-amber-800"}>
                {ai.mode === "llm"
                  ? "Classification and drafting are sent to the configured model. Deterministic guardrails still enforce escalation and block unapproved commitments."
                  : ai.degraded
                    ? "The configured provider rejected or did not answer the last request, so the built-in analyst is handling tickets. Requests are not blocked and every ticket records which engine produced it."
                    : "No usable model credential is configured. The built-in analyst handles classification, retrieval and grounded drafting, so the full workflow still works. Nothing is faked: every ticket records which engine produced it."}
              </p>
              {ai.retry_in_seconds ? (
                <p className="mt-1 text-[10.5px] text-amber-700">
                  Next provider attempt in {ai.retry_in_seconds}s (or use Test connection now).
                </p>
              ) : null}
            </div>
          </div>

          <dl className="mt-4 grid gap-x-6 gap-y-3 sm:grid-cols-2">
            <KeyValue label="Provider">{ai.provider}</KeyValue>
            <KeyValue label="Model">
              <span className="font-mono text-[12px]">{ai.model}</span>
            </KeyValue>
            <KeyValue label="Endpoint host">
              <span className="font-mono text-[12px]">{ai.base_url_host}</span>
            </KeyValue>
            <KeyValue label="API key">
              {ai.configured ? (
                <span className="inline-flex items-center gap-1 text-emerald-700">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Present on the server
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-amber-700">
                  <KeyRound className="h-3.5 w-3.5" /> Not configured
                </span>
              )}
            </KeyValue>
            <KeyValue label="Last success">
              {ai.last_success_at ? formatDateTime(ai.last_success_at) : "—"}
            </KeyValue>
            <KeyValue label="Last latency">
              {ai.last_latency_ms ? `${ai.last_latency_ms} ms` : "—"}
            </KeyValue>
          </dl>

          {ai.last_error ? (
            <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50/60 px-3.5 py-2.5">
              <p className="flex items-center gap-1.5 text-[11px] font-semibold text-rose-800">
                <XCircle className="h-3.5 w-3.5" /> Last provider error
              </p>
              <p className="mt-1 break-words font-mono text-[11px] leading-relaxed text-rose-700">
                {ai.last_error}
              </p>
              {ai.last_error_at ? (
                <p className="mt-1 text-[10px] text-rose-500">{formatDateTime(ai.last_error_at)}</p>
              ) : null}
            </div>
          ) : null}

          {testResult ? (
            <div
              className={`mt-4 flex items-start gap-2 rounded-lg border px-3.5 py-2.5 text-xs ${
                testResult.ok
                  ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                  : "border-rose-200 bg-rose-50 text-rose-800"
              }`}
            >
              {testResult.ok ? (
                <CheckCircle2 className="mt-0.5 h-3.5 w-3.5" />
              ) : (
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5" />
              )}
              <div>
                <p className="font-medium">{testResult.detail}</p>
                <p className="mt-0.5 text-[10.5px] opacity-80">
                  {testResult.provider} · {testResult.model}
                  {testResult.latency_ms ? ` · ${testResult.latency_ms} ms` : ""}
                </p>
              </div>
            </div>
          ) : null}

          {testError ? <div className="mt-3"><ErrorState message={testError} /></div> : null}

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => void testConnection()} disabled={testing}>
              {testing ? <Spinner className="h-3.5 w-3.5" /> : <RefreshCw className="h-3.5 w-3.5" />}
              Test connection
            </button>
            <span className="text-[10.5px] text-slate-400">
              Sends a tiny live request; it never creates a ticket.
            </span>
          </div>

          {!ai.configured ? (
            <div className="mt-4">
              <p className="mb-1.5 flex items-center gap-1.5 text-[11px] font-medium text-slate-600">
                <Terminal className="h-3.5 w-3.5" /> Enable a live model
              </p>
              <pre className="overflow-x-auto rounded-lg bg-slate-900 px-3.5 py-3 text-[11px] leading-relaxed text-slate-200">
{`# .env (never commit this file)
LLM_ENABLED=true
LLM_PROVIDER=OpenRouter
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=your-key
LLM_MODEL=google/gemma-4-31b-it:free`}
              </pre>
              <p className="mt-1.5 text-[10.5px] text-slate-400">
                Any OpenAI-compatible endpoint works, including a local Ollama server. Restart the API after
                editing.
              </p>
            </div>
          ) : null}
        </section>

        <section className="card p-5">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
              <Database className="h-4 w-4" />
            </span>
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Runtime</h2>
              <p className="text-[11px] text-slate-500">Single-node demo deployment.</p>
            </div>
          </div>
          <dl className="mt-4 space-y-3">
            <KeyValue label="Version">{status.app_version}</KeyValue>
            <KeyValue label="Database">SQLite (WAL)</KeyValue>
            <KeyValue label="Tickets stored">{status.counts.tickets}</KeyValue>
            <KeyValue label="Knowledge articles">{status.counts.articles}</KeyValue>
            <KeyValue label="Retrieval depth">Top {status.retrieval_top_k} articles</KeyValue>
            <KeyValue label="Demo reset">{status.demo_reset_enabled ? "Enabled" : "Disabled"}</KeyValue>
          </dl>
          <div className="mt-4 space-y-1.5 border-t border-slate-100 pt-3 text-[10.5px] text-slate-400">
            <p className="flex items-center gap-1.5">
              <Server className="h-3 w-3" /> FastAPI + SQLAlchemy 2
            </p>
            <p className="flex items-center gap-1.5">
              <Database className="h-3 w-3" /> Data persists across restarts
            </p>
            <a
              href="/docs"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 font-medium text-brand-600 hover:underline"
            >
              Open API docs <ArrowRight className="h-3 w-3" />
            </a>
          </div>
        </section>

        <section className="card p-5">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-50 text-sky-600">
              <Search className="h-4 w-4" />
            </span>
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Retrieval</h2>
              <p className="text-[11px] text-slate-500">BM25 with intent priors.</p>
            </div>
          </div>

          <ol className="mt-4 space-y-3">
            <Step index={1} title="Classify" description="Keyword + rule scoring picks category, intent, priority and escalation flags." />
            <Step index={2} title="Retrieve" description="BM25 over title, tags, summary and body, biased by category and intent." />
            <Step index={3} title="Draft" description="The model writes from retrieved excerpts only, or the template analyst quotes them." />
            <Step index={4} title="Guardrail" description="Escalation rules and commitment checks run after generation." />
          </ol>

          <form onSubmit={runSearch} className="mt-4 border-t border-slate-100 pt-3">
            <label className="label" htmlFor="retrieval-query">
              Try retrieval
            </label>
            <div className="flex gap-1.5">
              <input
                id="retrieval-query"
                className="input py-1.5 text-xs"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="e.g. refund window"
              />
              <button type="submit" className="btn btn-secondary btn-sm" disabled={searching}>
                {searching ? <Spinner className="h-3.5 w-3.5" /> : <Search className="h-3.5 w-3.5" />}
              </button>
            </div>
            {hits ? (
              <ul className="mt-2 space-y-1">
                {hits.length === 0 ? (
                  <li className="rounded bg-amber-50 px-2 py-1.5 text-[10.5px] text-amber-800">
                    No article matched — the assistant would escalate instead of guessing.
                  </li>
                ) : (
                  hits.map((hit) => (
                    <li
                      key={hit.slug}
                      className="flex items-center justify-between gap-2 rounded bg-slate-50 px-2 py-1.5 text-[10.5px]"
                    >
                      <span className="truncate text-slate-600">{hit.title}</span>
                      <span className="shrink-0 font-mono text-slate-400">
                        {Math.round(hit.score * 100)}%
                      </span>
                    </li>
                  ))
                )}
              </ul>
            ) : null}
          </form>
        </section>

        <section className="card p-5">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-50 text-violet-600">
              <FlaskConical className="h-4 w-4" />
            </span>
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Demo data</h2>
              <p className="text-[11px] text-slate-500">Nine scripted tickets, twenty articles.</p>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-2">
            {[
              { label: "New", value: status.counts.new },
              { label: "In progress", value: status.counts.in_progress },
              { label: "Escalated", value: status.counts.escalated },
              { label: "Resolved", value: status.counts.resolved },
            ].map((item) => (
              <div key={item.label} className="rounded-lg border border-slate-100 bg-slate-50/60 px-2.5 py-2">
                <p className="text-[10px] uppercase tracking-wide text-slate-400">{item.label}</p>
                <p className="mt-0.5 text-lg font-semibold text-slate-800">{item.value}</p>
              </div>
            ))}
          </div>

          <p className="mt-3 text-[11px] leading-relaxed text-slate-500">
            Reset deletes every ticket and restores the original demo set. Useful between demo runs.
          </p>

          {resetConfirm ? (
            <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50/60 p-2.5">
              <p className="text-[11px] font-medium text-rose-800">
                Delete all tickets and restore the demo seed?
              </p>
              <div className="mt-2 flex items-center justify-end gap-1.5">
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => setResetConfirm(false)}>
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-danger btn-sm"
                  onClick={() => void resetDemo()}
                  disabled={resetting || !status.demo_reset_enabled}
                >
                  {resetting ? <Spinner className="h-3.5 w-3.5" /> : <RefreshCw className="h-3.5 w-3.5" />}
                  Reset demo
                </button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              className="btn btn-secondary btn-sm mt-3"
              onClick={() => setResetConfirm(true)}
              disabled={!status.demo_reset_enabled}
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Reset demo data
            </button>
          )}
        </section>

        <section className="card p-5">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-50 text-amber-600">
              <ShieldCheck className="h-4 w-4" />
            </span>
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Limitations</h2>
              <p className="text-[11px] text-slate-500">What this hackathon build does not do.</p>
            </div>
          </div>
          <ul className="mt-3 space-y-2 text-[11.5px] leading-relaxed text-slate-600">
            <li className="flex gap-2">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
              No email or chat provider is connected. Approving a reply records it in the conversation only.
            </li>
            <li className="flex gap-2">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
              No order, payment or CRM lookup. The AI cannot see live order status, so it never invents one.
            </li>
            <li className="flex gap-2">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
              Single-tenant demo: no authentication, roles or audit export yet.
            </li>
            <li className="flex gap-2">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
              SQLite on one node; production needs Postgres and a background job queue.
            </li>
            <li className="flex gap-2">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
              Knowledge articles are fictional sample content written for the demo.
            </li>
          </ul>
          <div className="mt-3 border-t border-slate-100 pt-3">
            <p className="flex items-center gap-1.5 text-[10.5px] font-medium text-slate-500">
              <CheckCircle2 className="h-3 w-3 text-emerald-500" />
              {metrics?.totals.drafts_generated ?? 0} drafts generated ·{" "}
              {metrics?.totals.awaiting_review ?? 0} awaiting review
            </p>
          </div>
        </section>

        <section className="card p-5 xl:col-span-3">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
              <Terminal className="h-4 w-4" />
            </span>
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Configuration reference</h2>
              <p className="text-[11px] text-slate-500">
                Server-side environment variables. Secrets never reach the browser.
              </p>
            </div>
          </div>
          <div className="mt-3 grid gap-3 lg:grid-cols-2">
            <pre className="overflow-x-auto rounded-lg bg-slate-900 px-4 py-3 text-[11px] leading-relaxed text-slate-200">
{`DATABASE_URL=sqlite:///./data/supportpilot.db
SEED_ON_STARTUP=true
DEMO_RESET_ENABLED=true
CORS_ORIGINS=http://localhost:5173
RETRIEVAL_TOP_K=3`}
            </pre>
            <pre className="overflow-x-auto rounded-lg bg-slate-900 px-4 py-3 text-[11px] leading-relaxed text-slate-200">
{`LLM_ENABLED=true
LLM_PROVIDER=OpenRouter
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=<server-side secret>
LLM_MODEL=google/gemma-4-31b-it:free
LLM_TIMEOUT_SECONDS=45`}
            </pre>
          </div>
          <p className="mt-2 flex items-center gap-1.5 text-[10.5px] text-slate-400">
            <BookOpen className="h-3 w-3" /> Full setup and demo script live in the project README.
          </p>
        </section>
      </div>
    </div>
  );
}