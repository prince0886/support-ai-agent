import type { ReactNode } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  RefreshCw,
  type LucideIcon,
} from "lucide-react";

import {
  AI_MODE_LABEL,
  CATEGORY_META,
  DRAFT_STATUS_META,
  PRIORITY_META,
  SENTIMENT_META,
  STATUS_META,
} from "../lib/labels";
import type {
  AiMode,
  Category,
  DraftStatus,
  Priority,
  Sentiment,
  TicketStatus,
} from "../lib/types";

export function Badge({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <span className={`chip ${className}`}>{children}</span>;
}

export function StatusBadge({ status }: { status: TicketStatus }) {
  const meta = STATUS_META[status];
  return (
    <Badge className={meta.chip}>
      <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
      {meta.label}
    </Badge>
  );
}

export function PriorityBadge({ priority }: { priority: Priority }) {
  const meta = PRIORITY_META[priority];
  return (
    <Badge className={meta.chip}>
      <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
      {meta.label}
    </Badge>
  );
}

export function CategoryBadge({ category }: { category: Category }) {
  const meta = CATEGORY_META[category];
  return <Badge className={meta.chip}>{meta.label}</Badge>;
}

export function SentimentBadge({ sentiment }: { sentiment: Sentiment }) {
  const meta = SENTIMENT_META[sentiment];
  return <Badge className={meta.chip}>{meta.label}</Badge>;
}

export function DraftBadge({ status }: { status: DraftStatus }) {
  const meta = DRAFT_STATUS_META[status];
  return <Badge className={meta.chip}>{meta.label}</Badge>;
}

export function EngineBadge({
  mode,
  model,
}: {
  mode: AiMode;
  model?: string;
}) {
  const isLlm = mode === "llm";
  return (
    <Badge
      className={
        isLlm
          ? "bg-brand-50 text-brand-700 ring-brand-200"
          : "bg-slate-100 text-slate-600 ring-slate-200"
      }
    >
      <span className={`h-1.5 w-1.5 rounded-full ${isLlm ? "bg-brand-500" : "bg-slate-400"}`} />
      {AI_MODE_LABEL[mode]}
      {model ? <span className="font-normal opacity-70">· {model}</span> : null}
    </Badge>
  );
}

export function Spinner({ className = "h-4 w-4" }: { className?: string }) {
  return <Loader2 className={`animate-spin ${className}`} aria-hidden />;
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} />;
}

export function PageHeader({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight text-slate-900">{title}</h1>
        {subtitle ? <p className="mt-1 text-sm text-slate-500">{subtitle}</p> : null}
      </div>
      {children ? <div className="flex flex-wrap items-center gap-2">{children}</div> : null}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="card flex flex-col items-start gap-3 border-rose-200 bg-rose-50/40 p-5">
      <div className="flex items-center gap-2 text-sm font-medium text-rose-800">
        <AlertTriangle className="h-4 w-4" />
        Something went wrong
      </div>
      <p className="text-sm text-rose-700">{message}</p>
      {onRetry ? (
        <button type="button" className="btn btn-secondary btn-sm" onClick={onRetry}>
          <RefreshCw className="h-3.5 w-3.5" />
          Try again
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-14 text-center">
      <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-slate-100 text-slate-500">
        <Icon className="h-5 w-5" />
      </div>
      <p className="text-sm font-semibold text-slate-800">{title}</p>
      <p className="mt-1 max-w-sm text-sm text-slate-500">{description}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export function SuccessBanner({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
      <div>{children}</div>
    </div>
  );
}

export function ProgressBar({
  value,
  tone = "brand",
  className = "",
}: {
  value: number;
  tone?: "brand" | "emerald" | "amber" | "rose" | "slate";
  className?: string;
}) {
  const tones: Record<string, string> = {
    brand: "bg-brand-500",
    emerald: "bg-emerald-500",
    amber: "bg-amber-500",
    rose: "bg-rose-500",
    slate: "bg-slate-400",
  };
  return (
    <div className={`h-1.5 w-full overflow-hidden rounded-full bg-slate-100 ${className}`}>
      <div
        className={`h-full rounded-full ${tones[tone]}`}
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      />
    </div>
  );
}

export function KeyValue({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div>
      <dt className="text-[11px] font-medium uppercase tracking-wide text-slate-400">{label}</dt>
      <dd className="mt-0.5 text-sm text-slate-700">{children}</dd>
    </div>
  );
}