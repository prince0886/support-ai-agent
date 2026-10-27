import { ShieldAlert } from "lucide-react";
import { Link } from "react-router-dom";

import { avatarColor, initials, relativeTime } from "../lib/format";
import { PRIORITY_META, STATUS_META } from "../lib/labels";
import type { TicketSummary } from "../lib/types";
import { CategoryBadge, PriorityBadge, Skeleton } from "./ui";

export function TicketListItem({
  ticket,
  selected,
}: {
  ticket: TicketSummary;
  selected: boolean;
}) {
  return (
    <Link
      to={`/inbox/${ticket.id}`}
      className={`relative block border-b border-slate-100 px-3.5 py-3 transition ${
        selected ? "bg-brand-50/70" : "hover:bg-slate-50/80"
      }`}
    >
      {selected ? (
        <span className="absolute inset-y-0 left-0 w-[3px] bg-brand-500" aria-hidden />
      ) : null}
      <div className="flex gap-2.5">
        <div
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold ${avatarColor(
            ticket.customer_name,
          )}`}
        >
          {initials(ticket.customer_name)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-2">
            <p className="truncate text-[13px] font-semibold text-slate-800">
              {ticket.customer_name}
            </p>
            <span className="shrink-0 text-[10px] text-slate-400">
              {relativeTime(ticket.created_at)}
            </span>
          </div>
          <p className="mt-0.5 truncate text-xs font-medium text-slate-700">{ticket.subject}</p>
          <p className="mt-0.5 line-clamp-1 text-[11px] leading-relaxed text-slate-500">
            {ticket.preview}
          </p>
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            <PriorityBadge priority={ticket.priority} />
            <CategoryBadge category={ticket.category} />
            {ticket.requires_human ? (
              <span
                className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 ring-1 ring-inset ring-amber-200"
                title={ticket.risk_flags.join(", ")}
              >
                <ShieldAlert className="h-2.5 w-2.5" />
                Review
              </span>
            ) : null}
            <span className="ml-auto flex items-center gap-1 text-[10px] text-slate-400">
              <span className={`h-1.5 w-1.5 rounded-full ${STATUS_META[ticket.status].dot}`} />
              {STATUS_META[ticket.status].label}
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}

export function TicketListSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="divide-y divide-slate-100">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="flex gap-2.5 px-3.5 py-3">
          <Skeleton className="h-8 w-8 rounded-full" />
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-3 w-28" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-2/3" />
            <div className="flex gap-1.5 pt-1">
              <Skeleton className="h-4 w-14 rounded-full" />
              <Skeleton className="h-4 w-16 rounded-full" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export function priorityRank(priority: TicketSummary["priority"]): number {
  return PRIORITY_META[priority].rank;
}