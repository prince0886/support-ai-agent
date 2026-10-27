import {
  ArrowRight,
  CheckCircle2,
  Clock3,
  FolderOpen,
  Inbox,
  Plus,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import { ConfidenceRing, DistributionBars, PriorityMix, TrendChart } from "../components/charts";
import {
  CategoryBadge,
  EmptyState,
  EngineBadge,
  ErrorState,
  PageHeader,
  PriorityBadge,
  ProgressBar,
  Skeleton,
  StatusBadge,
} from "../components/ui";
import { useNewTicket } from "../components/NewTicketModal";
import { relativeTime } from "../lib/format";
import {
  CATEGORY_META,
  CATEGORY_ORDER,
  PRIORITY_META,
  PRIORITY_ORDER,
} from "../lib/labels";
import type { Metrics } from "../lib/types";
import { useApp } from "../store/AppStore";

function MetricCard({
  label,
  value,
  hint,
  icon: Icon,
  tone,
}: {
  label: string;
  value: number | string;
  hint: string;
  icon: typeof Inbox;
  tone: "brand" | "sky" | "amber" | "emerald";
}) {
  const tones = {
    brand: "bg-brand-50 text-brand-600",
    sky: "bg-sky-50 text-sky-600",
    amber: "bg-amber-50 text-amber-600",
    emerald: "bg-emerald-50 text-emerald-600",
  };
  return (
    <div className="card p-4">
      <div className="flex items-start justify-between">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">{label}</p>
        <span className={`flex h-8 w-8 items-center justify-center rounded-lg ${tones[tone]}`}>
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <p className="mt-2 text-[26px] font-semibold leading-none tracking-tight text-slate-900">
        {value}
      </p>
      <p className="mt-2 text-xs text-slate-500">{hint}</p>
    </div>
  );
}

function OverviewSkeleton() {
  return (
    <div>
      <div className="mb-6 space-y-2">
        <Skeleton className="h-7 w-40" />
        <Skeleton className="h-4 w-80" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((item) => (
          <div key={item} className="card p-4">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="mt-4 h-8 w-16" />
            <Skeleton className="mt-3 h-3 w-32" />
          </div>
        ))}
      </div>
      <div className="mt-5 grid gap-5 xl:grid-cols-3">
        <div className="card p-5 xl:col-span-2">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="mt-6 h-[190px] w-full" />
        </div>
        <div className="card p-5">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="mt-6 h-24 w-full" />
          <Skeleton className="mt-4 h-24 w-full" />
        </div>
      </div>
    </div>
  );
}

function AiPerformance({ metrics }: { metrics: Metrics }) {
  const totals = metrics.totals;
  return (
    <section className="card flex flex-col p-5">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">AI performance</h2>
          <p className="mt-0.5 text-xs text-slate-500">Automation with a human checkpoint.</p>
        </div>
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
          <Sparkles className="h-4 w-4" />
        </span>
      </div>

      <div className="mt-4 flex items-center gap-3 rounded-lg border border-slate-100 bg-slate-50/60 p-3">
        <ConfidenceRing value={totals.avg_confidence} />
        <div>
          <p className="text-xs font-medium text-slate-700">Average analysis confidence</p>
          <p className="mt-0.5 text-[11px] text-slate-500">
            {totals.drafts_generated} drafts generated across {totals.total} tickets
          </p>
        </div>
      </div>

      <div className="mt-4 space-y-3.5">
        <div>
          <div className="mb-1.5 flex items-center justify-between text-xs">
            <span className="text-slate-600">Human review rate</span>
            <span className="font-semibold text-slate-900">{totals.human_review_rate}%</span>
          </div>
          <ProgressBar value={totals.human_review_rate} tone="amber" />
        </div>
        <div>
          <div className="mb-1.5 flex items-center justify-between text-xs">
            <span className="text-slate-600">Resolved without escalation</span>
            <span className="font-semibold text-slate-900">
              {totals.resolved_without_escalation}
            </span>
          </div>
          <ProgressBar
            value={
              totals.resolved
                ? (totals.resolved_without_escalation / totals.resolved) * 100
                : 0
            }
            tone="emerald"
          />
        </div>
        <div>
          <div className="mb-1.5 flex items-center justify-between text-xs">
            <span className="text-slate-600">Queue resolution rate</span>
            <span className="font-semibold text-slate-900">{totals.resolve_rate}%</span>
          </div>
          <ProgressBar value={totals.resolve_rate} tone="brand" />
        </div>
      </div>

      <div className="mt-auto flex items-center gap-1.5 pt-4 text-[11px] text-slate-400">
        <Clock3 className="h-3 w-3" />
        Recomputed from ticket rows, not hardcoded.
      </div>
    </section>
  );
}

export function Overview() {
  const { metrics, status, loading, error, refresh } = useApp();
  const { open } = useNewTicket();
  const navigate = useNavigate();

  if (loading && !metrics) return <OverviewSkeleton />;
  if (error && !metrics) {
    return (
      <div>
        <PageHeader title="Overview" subtitle="AI triage across the support queue." />
        <ErrorState message={error} onRetry={() => void refresh()} />
      </div>
    );
  }
  if (!metrics) return null;

  const totals = metrics.totals;

  return (
    <div>
      <PageHeader
        title="Overview"
        subtitle="How SupportPilot is triaging the Northwind Supply support queue."
      >
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => void refresh()}
          title="Refresh metrics"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
        <button type="button" className="btn btn-primary" onClick={open}>
          <Plus className="h-4 w-4" />
          New ticket
        </button>
      </PageHeader>

      {error ? (
        <div className="mb-4">
          <ErrorState message={error} onRetry={() => void refresh()} />
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Total tickets"
          value={totals.total}
          hint={`${totals.new} new · ${totals.in_progress} in progress`}
          icon={Inbox}
          tone="brand"
        />
        <MetricCard
          label="Open queue"
          value={totals.open}
          hint={`${totals.urgent} urgent · ${totals.awaiting_review} awaiting review`}
          icon={FolderOpen}
          tone="sky"
        />
        <MetricCard
          label="Needs a human"
          value={totals.awaiting_review}
          hint={`${totals.human_review_rate}% of all tickets`}
          icon={ShieldAlert}
          tone="amber"
        />
        <MetricCard
          label="Resolved"
          value={totals.resolved}
          hint={`${totals.resolve_rate}% of the queue closed`}
          icon={CheckCircle2}
          tone="emerald"
        />
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-3">
        <section className="card p-5 xl:col-span-2">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Ticket volume</h2>
              <p className="mt-0.5 text-xs text-slate-500">Received vs resolved over the last 7 days.</p>
            </div>
            <span className="flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700 ring-1 ring-inset ring-emerald-200">
              <TrendingUp className="h-3 w-3" />
              Live
            </span>
          </div>
          <div className="mt-3">
            <TrendChart data={metrics.trend} />
          </div>
        </section>

        <AiPerformance metrics={metrics} />
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-3">
        <section className="card p-5">
          <h2 className="text-sm font-semibold text-slate-900">Tickets by category</h2>
          <p className="mt-0.5 text-xs text-slate-500">Automatic classification across the queue.</p>
          <div className="mt-4">
            <DistributionBars
              items={CATEGORY_ORDER.map((category) => ({
                key: category,
                label: CATEGORY_META[category].label,
                value: metrics.by_category[category] ?? 0,
                bar: CATEGORY_META[category].bar,
              }))}
            />
          </div>
        </section>

        <section className="card p-5">
          <h2 className="text-sm font-semibold text-slate-900">Priority mix</h2>
          <p className="mt-0.5 text-xs text-slate-500">Urgency scored from content and impact.</p>
          <div className="mt-5">
            <PriorityMix
              items={PRIORITY_ORDER.map((priority) => ({
                key: priority,
                label: PRIORITY_META[priority].label,
                value: metrics.by_priority[priority] ?? 0,
                bar: PRIORITY_META[priority].bar,
                dot: PRIORITY_META[priority].dot,
              }))}
            />
          </div>
          <p className="mt-5 rounded-lg bg-slate-50 px-3 py-2 text-[11px] leading-relaxed text-slate-500">
            A ticket is escalated for policy exceptions, payment decisions, missing parcels, security
            concerns and blocking outages.
          </p>
        </section>

        <section className="card flex flex-col p-5">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Needs human review</h2>
              <p className="mt-0.5 text-xs text-slate-500">Highest priority first.</p>
            </div>
            <Link to="/inbox?requires_human=true" className="text-xs font-medium text-brand-600 hover:underline">
              View all
            </Link>
          </div>

          {metrics.human_review.length === 0 ? (
            <EmptyState
              icon={CheckCircle2}
              title="Review queue is clear"
              description="Every open ticket is routine. AI drafts are ready for one-click approval."
            />
          ) : (
            <ul className="mt-3 divide-y divide-slate-100">
              {metrics.human_review.map((ticket) => (
                <li key={ticket.id}>
                  <Link
                    to={`/inbox/${ticket.id}`}
                    className="group flex items-start gap-2.5 py-2.5"
                  >
                    <span
                      className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                        PRIORITY_META[ticket.priority].dot
                      }`}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs font-medium text-slate-800 group-hover:text-brand-700">
                        {ticket.subject}
                      </p>
                      <p className="mt-0.5 truncate text-[11px] text-slate-500">
                        {ticket.customer_name} · {relativeTime(ticket.created_at)}
                      </p>
                    </div>
                    <ArrowRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-300 group-hover:text-brand-500" />
                  </Link>
                </li>
              ))}
            </ul>
          )}
          <div className="mt-auto pt-3">
            <p className="flex items-center gap-1.5 text-[11px] text-slate-400">
              <ShieldAlert className="h-3 w-3" />
              AI never approves a refund or an exception.
            </p>
          </div>
        </section>
      </div>

      <section className="card mt-5 overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Recent tickets</h2>
            <p className="mt-0.5 text-xs text-slate-500">Latest messages across every channel.</p>
          </div>
          <Link to="/inbox" className="btn btn-secondary btn-sm">
            Open inbox <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/60 text-[10px] uppercase tracking-wider text-slate-500">
                <th className="px-5 py-2.5 font-semibold">Ticket</th>
                <th className="px-4 py-2.5 font-semibold">Customer</th>
                <th className="px-4 py-2.5 font-semibold">Category</th>
                <th className="px-4 py-2.5 font-semibold">Priority</th>
                <th className="px-4 py-2.5 font-semibold">Status</th>
                <th className="px-4 py-2.5 font-semibold">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {metrics.recent.map((ticket) => (
                <tr
                  key={ticket.id}
                  className="cursor-pointer transition hover:bg-slate-50/80"
                  onClick={() => navigate(`/inbox/${ticket.id}`)}
                >
                  <td className="px-5 py-3">
                    <p className="font-mono text-[11px] text-slate-400">{ticket.reference}</p>
                    <p className="mt-0.5 max-w-[290px] truncate text-sm font-medium text-slate-800">
                      {ticket.subject}
                    </p>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-600">{ticket.customer_name}</td>
                  <td className="px-4 py-3">
                    <CategoryBadge category={ticket.category} />
                  </td>
                  <td className="px-4 py-3">
                    <PriorityBadge priority={ticket.priority} />
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={ticket.status} />
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500">
                    {relativeTime(ticket.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 px-5 py-3 text-[11px] text-slate-400">
          <span>
            {status?.ai.mode === "llm" ? "Live model" : "Deterministic fallback"} · retrieval top{" "}
            {status?.retrieval_top_k ?? 3} · {status?.counts.articles ?? 0} knowledge articles
          </span>
          <EngineBadge
            mode={status?.ai.mode ?? "fallback"}
            model={status?.ai.mode === "llm" ? status.ai.model : "analyst v1"}
          />
        </div>
      </section>
    </div>
  );
}