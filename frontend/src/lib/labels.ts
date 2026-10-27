import type {
  AiMode,
  Category,
  DraftStatus,
  Priority,
  Sentiment,
  TicketStatus,
} from "./types";

export interface Meta {
  label: string;
  chip: string;
  dot: string;
  bar: string;
}

export const CATEGORY_META: Record<Category, Meta> = {
  billing: {
    label: "Billing",
    chip: "bg-amber-50 text-amber-700 ring-amber-200",
    dot: "bg-amber-500",
    bar: "bg-amber-400",
  },
  refund: {
    label: "Refund",
    chip: "bg-violet-50 text-violet-700 ring-violet-200",
    dot: "bg-violet-500",
    bar: "bg-violet-400",
  },
  shipping: {
    label: "Shipping",
    chip: "bg-sky-50 text-sky-700 ring-sky-200",
    dot: "bg-sky-500",
    bar: "bg-sky-400",
  },
  technical_support: {
    label: "Technical Support",
    chip: "bg-rose-50 text-rose-700 ring-rose-200",
    dot: "bg-rose-500",
    bar: "bg-rose-400",
  },
  general_inquiry: {
    label: "General Inquiry",
    chip: "bg-slate-100 text-slate-600 ring-slate-200",
    dot: "bg-slate-400",
    bar: "bg-slate-400",
  },
};

export const PRIORITY_META: Record<Priority, Meta & { rank: number }> = {
  low: {
    label: "Low",
    chip: "bg-slate-100 text-slate-600 ring-slate-200",
    dot: "bg-slate-400",
    bar: "bg-slate-400",
    rank: 4,
  },
  medium: {
    label: "Medium",
    chip: "bg-sky-50 text-sky-700 ring-sky-200",
    dot: "bg-sky-500",
    bar: "bg-sky-400",
    rank: 3,
  },
  high: {
    label: "High",
    chip: "bg-orange-50 text-orange-700 ring-orange-200",
    dot: "bg-orange-500",
    bar: "bg-orange-400",
    rank: 2,
  },
  urgent: {
    label: "Urgent",
    chip: "bg-rose-50 text-rose-700 ring-rose-200",
    dot: "bg-rose-500",
    bar: "bg-rose-400",
    rank: 1,
  },
};

export const STATUS_META: Record<TicketStatus, Meta> = {
  new: {
    label: "New",
    chip: "bg-blue-50 text-blue-700 ring-blue-200",
    dot: "bg-blue-500",
    bar: "bg-blue-400",
  },
  in_progress: {
    label: "In Progress",
    chip: "bg-amber-50 text-amber-700 ring-amber-200",
    dot: "bg-amber-500",
    bar: "bg-amber-400",
  },
  escalated: {
    label: "Escalated",
    chip: "bg-rose-50 text-rose-700 ring-rose-200",
    dot: "bg-rose-500",
    bar: "bg-rose-400",
  },
  resolved: {
    label: "Resolved",
    chip: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    dot: "bg-emerald-500",
    bar: "bg-emerald-400",
  },
};

export const SENTIMENT_META: Record<Sentiment, { label: string; chip: string }> = {
  positive: { label: "Positive", chip: "bg-emerald-50 text-emerald-700 ring-emerald-200" },
  neutral: { label: "Neutral", chip: "bg-slate-100 text-slate-600 ring-slate-200" },
  frustrated: { label: "Frustrated", chip: "bg-orange-50 text-orange-700 ring-orange-200" },
  angry: { label: "Angry", chip: "bg-rose-50 text-rose-700 ring-rose-200" },
};

export const DRAFT_STATUS_META: Record<DraftStatus, { label: string; chip: string }> = {
  draft: { label: "AI draft", chip: "bg-amber-50 text-amber-700 ring-amber-200" },
  edited: { label: "Edited by human", chip: "bg-sky-50 text-sky-700 ring-sky-200" },
  approved: { label: "Approved", chip: "bg-emerald-50 text-emerald-700 ring-emerald-200" },
};

export const AI_MODE_LABEL: Record<AiMode, string> = {
  llm: "Live LLM",
  fallback: "Deterministic analyst",
};

export const CATEGORY_ORDER: Category[] = [
  "shipping",
  "refund",
  "billing",
  "technical_support",
  "general_inquiry",
];

export const PRIORITY_ORDER: Priority[] = ["urgent", "high", "medium", "low"];

export const EVENT_LABEL: Record<string, string> = {
  created: "Ticket received",
  flagged: "Flagged for review",
  guardrail: "Safety guardrail",
  reanalyzed: "Re-analyzed",
  draft_edited: "Draft edited",
  approved: "Reply approved",
  updated: "Ticket updated",
  escalated: "Escalated",
  resolved: "Resolved",
  reopened: "Reopened",
  note_added: "Internal note",
  reply_sent: "Reply sent",
  status_changed: "Status changed",
};