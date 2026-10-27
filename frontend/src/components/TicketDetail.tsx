import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  BookOpen,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleDot,
  Clock3,
  Mail,
  MessageSquare,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  Sparkles,
  StickyNote,
  UserRound,
  Zap,
} from "lucide-react";

import { api, errorMessage } from "../lib/api";
import { formatDateTime, relativeTime } from "../lib/format";
import { useTicket } from "../lib/hooks";
import {
  CATEGORY_META,
  DRAFT_STATUS_META,
  EVENT_LABEL,
  PRIORITY_META,
  SENTIMENT_META,
  STATUS_META,
} from "../lib/labels";
import type { TicketDetail } from "../lib/types";
import { useApp } from "../store/AppStore";
import { ConfidenceRing } from "./charts";
import {
  Badge,
  CategoryBadge,
  DraftBadge,
  EngineBadge,
  ErrorState,
  KeyValue,
  PriorityBadge,
  ProgressBar,
  SentimentBadge,
  Skeleton,
  Spinner,
  StatusBadge,
} from "./ui";

function DetailSkeleton() {
  return (
    <div className="space-y-4">
      <div className="card p-5">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="mt-3 h-6 w-2/3" />
        <Skeleton className="mt-2 h-3 w-1/2" />
        <Skeleton className="mt-5 h-24 w-full" />
      </div>
      <div className="card p-5">
        <Skeleton className="h-4 w-32" />
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[0, 1, 2, 3].map((item) => (
            <Skeleton key={item} className="h-14 w-full" />
          ))}
        </div>
      </div>
    </div>
  );
}

function DraftEditor({
  ticket,
  draft,
  onDraftChange,
  busy,
  onSave,
  onApprove,
  onReanalyze,
}: {
  ticket: TicketDetail;
  draft: string;
  onDraftChange: (value: string) => void;
  busy: string | null;
  onSave: () => void;
  onApprove: () => void;
  onReanalyze: () => void;
}) {
  const dirty = draft !== ticket.draft_reply;
  const disabled = busy !== null;

  return (
    <div className="overflow-hidden rounded-xl border border-amber-200 bg-white shadow-card">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-amber-100 bg-amber-50/70 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <Sparkles className="h-3.5 w-3.5 text-amber-600" />
          <p className="text-xs font-semibold text-amber-900">AI draft — not sent</p>
          <DraftBadge status={ticket.draft_status} />
        </div>
        <EngineBadge mode={ticket.ai_mode} model={ticket.ai_mode === "llm" ? ticket.ai_model : "analyst v1"} />
      </div>

      <div className="p-4">
        <textarea
          value={draft}
          onChange={(event) => onDraftChange(event.target.value)}
          disabled={disabled}
          className="input min-h-[240px] resize-y bg-white text-[13px] leading-relaxed"
          aria-label="Draft reply"
        />
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-400">
          <span>
            {draft.length} characters · grounded in {ticket.sources.length} retrieved article
            {ticket.sources.length === 1 ? "" : "s"}
          </span>
          {dirty ? (
            <span className="font-medium text-amber-600">Unsaved edits</span>
          ) : (
            <span>Edit freely before approving</span>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 bg-slate-50/60 px-4 py-3">
        <p className="text-[11px] text-slate-500">
          Approval records the reply in the conversation. Nothing is sent automatically.
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" className="btn btn-ghost btn-sm" onClick={onReanalyze} disabled={disabled}>
            {busy === "reanalyze" ? <Spinner className="h-3.5 w-3.5" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Re-run AI
          </button>
          <button type="button" className="btn btn-secondary btn-sm" onClick={onSave} disabled={disabled || !dirty}>
            {busy === "save" ? <Spinner className="h-3.5 w-3.5" /> : null}
            Save draft
          </button>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={onApprove}
            disabled={disabled || !draft.trim()}
          >
            {busy === "approve" ? <Spinner className="h-3.5 w-3.5" /> : <Check className="h-3.5 w-3.5" />}
            Approve & send
          </button>
        </div>
      </div>
    </div>
  );
}

export function TicketDetailPanel({
  ticketId,
  onChanged,
}: {
  ticketId: number;
  onChanged: () => void;
}) {
  const { ticket, setTicket, loading, error, reload } = useTicket(ticketId);
  const { status: systemStatus, toast } = useApp();

  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [confirmResolve, setConfirmResolve] = useState(false);
  const [escalating, setEscalating] = useState(false);
  const [escalationReason, setEscalationReason] = useState("");
  const [noteOpen, setNoteOpen] = useState(false);
  const [note, setNote] = useState("");
  const [showAllEvents, setShowAllEvents] = useState(false);

  useEffect(() => {
    if (!ticket) return;
    setDraft(ticket.draft_reply);
    setEscalationReason(ticket.escalation_reason ?? "");
    setEscalating(false);
    setConfirmResolve(false);
    setNoteOpen(false);
    setNote("");
    setShowAllEvents(false);
    // Only reset the editor when a different ticket is opened.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticket?.id]);

  const perform = async (label: string, action: () => Promise<TicketDetail>, message: string) => {
    setBusy(label);
    try {
      const updated = await action();
      setTicket(updated);
      setDraft(updated.draft_reply);
      setConfirmResolve(false);
      setEscalating(false);
      onChanged();
      toast(message, "success");
    } catch (cause) {
      toast(errorMessage(cause), "error");
    } finally {
      setBusy(null);
    }
  };

  if (loading && !ticket) return <DetailSkeleton />;
  if (error && !ticket) {
    return (
      <ErrorState
        message={error}
        onRetry={() => {
          void reload();
        }}
      />
    );
  }
  if (!ticket) return null;

  const isResolved = ticket.status === "resolved";
  const isApproved = Boolean(ticket.approved_reply) && ticket.draft_status === "approved";
  const nonCustomerMessages = ticket.messages.filter((message) => message.role !== "customer");
  const events = showAllEvents ? ticket.events : ticket.events.slice(-7);
  const disabled = busy !== null;

  const copyState = busy === "approve" ? "Approving…" : null;

  return (
    <div className="animate-fade-in space-y-4">
      <div className="card p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-[11px] font-medium text-slate-400">
                {ticket.reference}
              </span>
              <StatusBadge status={ticket.status} />
              <PriorityBadge priority={ticket.priority} />
              {ticket.requires_human ? (
                <Badge className="bg-amber-50 text-amber-700 ring-amber-200">
                  <ShieldAlert className="h-2.5 w-2.5" /> Human review
                </Badge>
              ) : (
                <Badge className="bg-emerald-50 text-emerald-700 ring-emerald-200">
                  <CheckCircle2 className="h-2.5 w-2.5" /> Routine
                </Badge>
              )}
            </div>
            <h2 className="mt-2 text-xl font-semibold tracking-tight text-slate-900">
              {ticket.subject}
            </h2>
            <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-500">
              <span className="font-medium text-slate-700">{ticket.customer_name}</span>
              {ticket.customer_email ? <span>{ticket.customer_email}</span> : null}
              <span className="text-slate-300">·</span>
              <span className="inline-flex items-center gap-1 capitalize">
                <Mail className="h-3 w-3" /> {ticket.channel}
              </span>
              <span className="text-slate-300">·</span>
              <span title={formatDateTime(ticket.created_at)}>
                opened {relativeTime(ticket.created_at)}
              </span>
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {!isResolved ? (
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => {
                  setEscalating((value) => !value);
                  setConfirmResolve(false);
                }}
                disabled={disabled}
              >
                <ShieldAlert className="h-3.5 w-3.5" />
                Escalate
              </button>
            ) : (
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => void perform("reopen", () => api.reopen(ticket.id), "Ticket reopened.")}
                disabled={disabled}
              >
                {busy === "reopen" ? <Spinner className="h-3.5 w-3.5" /> : <RotateCcw className="h-3.5 w-3.5" />}
                Reopen
              </button>
            )}
            {!isResolved ? (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => {
                  setConfirmResolve(true);
                  setEscalating(false);
                }}
                disabled={disabled}
              >
                <Check className="h-3.5 w-3.5" />
                Resolve
              </button>
            ) : null}
          </div>
        </div>

        {escalating ? (
          <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50/60 p-3">
            <label className="label text-amber-900" htmlFor="escalation-reason">
              Why does this need a human?
            </label>
            <textarea
              id="escalation-reason"
              className="input min-h-[80px] text-[13px]"
              value={escalationReason}
              onChange={(event) => setEscalationReason(event.target.value)}
              placeholder="e.g. Customer is asking for a refund outside the 30-day window."
            />
            <div className="mt-2 flex items-center justify-end gap-2">
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setEscalating(false)}
                disabled={disabled}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={disabled || escalationReason.trim().length < 3}
                onClick={() =>
                  void perform(
                    "escalate",
                    () => api.escalate(ticket.id, escalationReason.trim()),
                    "Ticket escalated to a human specialist.",
                  )
                }
              >
                {busy === "escalate" ? <Spinner className="h-3.5 w-3.5" /> : <ShieldAlert className="h-3.5 w-3.5" />}
                Escalate ticket
              </button>
            </div>
          </div>
        ) : null}

        {confirmResolve ? (
          <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50/60 p-3">
            <div className="flex items-start gap-2">
              <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600" />
              <div className="text-xs text-emerald-900">
                <p className="font-semibold">Resolve this ticket?</p>
                <p className="mt-0.5 text-emerald-800">
                  {isApproved
                    ? "The approved reply stays in the conversation history."
                    : "The current draft will be recorded as the approved reply and marked as sent."}
                </p>
              </div>
            </div>
            <div className="mt-2 flex items-center justify-end gap-2">
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setConfirmResolve(false)}
                disabled={disabled}
              >
                Keep open
              </button>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={disabled}
                onClick={() =>
                  void perform(
                    "resolve",
                    () =>
                      api.resolve(
                        ticket.id,
                        isApproved ? undefined : draft.trim() || undefined,
                        undefined,
                      ),
                    "Ticket resolved.",
                  )
                }
              >
                {busy === "resolve" ? <Spinner className="h-3.5 w-3.5" /> : <Check className="h-3.5 w-3.5" />}
                Confirm resolve
              </button>
            </div>
          </div>
        ) : null}
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_286px]">
        <div className="min-w-0 space-y-4">
          <section className="card p-4">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-slate-400" />
              <h3 className="text-sm font-semibold text-slate-900">Customer request</h3>
              <span className="ml-auto text-[10px] text-slate-400">
                {formatDateTime(ticket.created_at)}
              </span>
            </div>
            <div className="mt-3 flex gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-500">
                <UserRound className="h-4 w-4" />
              </div>
              <div className="min-w-0 flex-1 rounded-lg rounded-tl-none border border-slate-100 bg-slate-50/70 px-3.5 py-3">
                <p className="text-xs font-semibold text-slate-800">
                  {ticket.customer_name}
                  {ticket.customer_email ? (
                    <span className="ml-1.5 font-normal text-slate-400">{ticket.customer_email}</span>
                  ) : null}
                </p>
                <p className="mt-1.5 whitespace-pre-wrap text-[13px] leading-relaxed text-slate-700">
                  {ticket.message}
                </p>
              </div>
            </div>
          </section>

          <section className="card p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-brand-500" />
                <h3 className="text-sm font-semibold text-slate-900">AI analysis</h3>
              </div>
              <EngineBadge
                mode={ticket.ai_mode}
                model={ticket.ai_mode === "llm" ? ticket.ai_model : "analyst v1"}
              />
            </div>

            <div className="mt-3 grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
              <div className="space-y-2.5">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Category</p>
                  <div className="mt-1">
                    <CategoryBadge category={ticket.category} />
                  </div>
                </div>
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Priority</p>
                  <div className="mt-1 flex items-center gap-1.5">
                    <PriorityBadge priority={ticket.priority} />
                    <SentimentBadge sentiment={ticket.sentiment} />
                  </div>
                </div>
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Intent</p>
                  <p className="mt-1 text-[13px] font-medium text-slate-700">{ticket.intent}</p>
                </div>
              </div>
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                  Why this classification
                </p>
                <p className="mt-1.5 text-xs leading-relaxed text-slate-600">
                  {ticket.classification_reason}
                </p>
              </div>
              <div className="flex flex-col items-center justify-start gap-1 rounded-lg border border-slate-100 bg-slate-50/60 px-3 py-2">
                <ConfidenceRing value={Math.round(ticket.confidence * 100)} />
                <span className="text-[10px] text-slate-500">confidence</span>
              </div>
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-slate-100 pt-3">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                Escalation triggers
              </span>
              {ticket.risk_flags.length === 0 ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700 ring-1 ring-inset ring-emerald-200">
                  <CheckCircle2 className="h-2.5 w-2.5" /> None detected
                </span>
              ) : (
                ticket.risk_flags.map((flag) => (
                  <span
                    key={flag}
                    className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-800 ring-1 ring-inset ring-amber-200"
                  >
                    <ShieldAlert className="h-2.5 w-2.5" />
                    {flag}
                  </span>
                ))
              )}
            </div>
          </section>

          <section className="card p-4">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-slate-400" />
                <h3 className="text-sm font-semibold text-slate-900">Knowledge used</h3>
              </div>
              <span className="text-[10px] text-slate-400">
                BM25 retrieval · {systemStatus?.counts.articles ?? 0} articles
              </span>
            </div>

            {ticket.sources.length === 0 ? (
              <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
                No article matched this request, so the reply states that the answer is unavailable and the
                ticket is routed to a human.
              </p>
            ) : (
              <ul className="mt-3 space-y-2.5">
                {ticket.sources.map((source, index) => (
                  <li key={`${source.slug}-${source.id}`} className="rounded-lg border border-slate-100 p-3">
                    <div className="flex items-start gap-2">
                      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded bg-slate-100 text-[10px] font-semibold text-slate-500">
                        {index + 1}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <Link
                            to={`/knowledge?slug=${source.slug}`}
                            className="truncate text-xs font-semibold text-slate-800 hover:text-brand-700 hover:underline"
                          >
                            {source.title}
                          </Link>
                          <CategoryBadge category={source.category} />
                        </div>
                        <div className="mt-1.5 flex items-center gap-2">
                          <ProgressBar
                            value={Math.round(source.score * 100)}
                            tone="brand"
                            className="max-w-[180px]"
                          />
                          <span className="text-[10px] font-medium tabular-nums text-slate-400">
                            {Math.round(source.score * 100)}% match
                          </span>
                        </div>
                        <blockquote className="mt-2 border-l-2 border-slate-200 pl-2.5 text-[11.5px] italic leading-relaxed text-slate-500">
                          {source.excerpt}
                        </blockquote>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {isResolved ? (
            <div className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-xs text-emerald-800">
              <CheckCircle2 className="mt-0.5 h-4 w-4" />
              <span>
                Resolved {relativeTime(ticket.resolved_at)}. Reopen the ticket if the customer replies again.
              </span>
            </div>
          ) : null}

          {isApproved && ticket.approved_reply ? (
            <section className="overflow-hidden rounded-xl border border-emerald-200 bg-white shadow-card">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-emerald-100 bg-emerald-50/70 px-4 py-2.5">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                  <p className="text-xs font-semibold text-emerald-900">Human-approved reply</p>
                  <Badge className="bg-emerald-100 text-emerald-800 ring-emerald-200">Sent</Badge>
                </div>
                <span className="text-[10px] text-emerald-700">
                  {formatDateTime(ticket.approved_at)}
                </span>
              </div>
              <div className="p-4">
                <div className="whitespace-pre-wrap rounded-lg border border-emerald-100 bg-emerald-50/30 px-4 py-3 text-[13px] leading-relaxed text-slate-700">
                  {ticket.approved_reply}
                </div>
                <p className="mt-2 text-[11px] text-slate-400">
                  Approved by Agent Rhea. Delivery is simulated in this demo (no email provider connected).
                </p>
                {ticket.draft_reply !== ticket.approved_reply ? (
                  <details className="mt-3 rounded-lg border border-slate-100 bg-slate-50/60 px-3 py-2">
                    <summary className="cursor-pointer text-[11px] font-medium text-slate-500">
                      View the original AI draft
                    </summary>
                    <p className="mt-2 whitespace-pre-wrap text-[11.5px] leading-relaxed text-slate-500">
                      {ticket.draft_reply}
                    </p>
                  </details>
                ) : null}
              </div>
            </section>
          ) : isResolved ? (
            // A resolved ticket is immutable until reopened, so the draft is
            // shown read-only rather than offering actions the API rejects.
            <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-card">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 bg-slate-50/80 px-4 py-2.5">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-3.5 w-3.5 text-slate-500" />
                  <p className="text-xs font-semibold text-slate-700">AI draft — read only</p>
                  <DraftBadge status={ticket.draft_status} />
                </div>
                <span className="text-[10.5px] text-slate-500">Ticket resolved</span>
              </div>
              <div className="p-4">
                <div className="whitespace-pre-wrap rounded-lg border border-slate-100 bg-slate-50/50 px-4 py-3 text-[13px] leading-relaxed text-slate-600">
                  {ticket.draft_reply}
                </div>
                <p className="mt-2 text-[11px] text-slate-400">
                  Reopen the ticket to edit or approve this reply.
                </p>
              </div>
            </section>
          ) : (
            <section>
              <DraftEditor
                ticket={ticket}
                draft={draft}
                onDraftChange={setDraft}
                busy={busy}
                onSave={() =>
                  void perform("save", () => api.saveDraft(ticket.id, draft), "Draft saved.")
                }
                onApprove={() =>
                  void perform(
                    "approve",
                    () => api.approve(ticket.id, draft),
                    copyState ? "Reply approved and recorded." : "Reply approved and recorded as sent.",
                  )
                }
                onReanalyze={() =>
                  void perform(
                    "reanalyze",
                    () => api.reanalyze(ticket.id),
                    "Re-analysis complete. Review the new draft.",
                  )
                }
              />
            </section>
          )}

          <section className="card p-4">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Clock3 className="h-4 w-4 text-slate-400" />
                <h3 className="text-sm font-semibold text-slate-900">Conversation history</h3>
              </div>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setNoteOpen((value) => !value)}
              >
                <StickyNote className="h-3.5 w-3.5" />
                Internal note
              </button>
            </div>

            {noteOpen ? (
              <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50/50 p-3">
                <textarea
                  className="input min-h-[70px] text-[13px]"
                  placeholder="Only your team can see this note…"
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                />
                <div className="mt-2 flex items-center justify-end gap-2">
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => {
                      setNoteOpen(false);
                      setNote("");
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={disabled || note.trim().length === 0}
                    onClick={() =>
                      void perform(
                        "note",
                        async () => {
                          const updated = await api.addMessage(ticket.id, note.trim(), true);
                          setNote("");
                          setNoteOpen(false);
                          return updated;
                        },
                        "Internal note added.",
                      )
                    }
                  >
                    {busy === "note" ? <Spinner className="h-3.5 w-3.5" /> : <StickyNote className="h-3.5 w-3.5" />}
                    Add note
                  </button>
                </div>
              </div>
            ) : null}

            <div className="mt-3 space-y-2.5">
              {nonCustomerMessages.length === 0 ? (
                <p className="rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500">
                  No agent activity yet. Approving the draft records the reply here.
                </p>
              ) : (
                nonCustomerMessages.map((message) => (
                  <div
                    key={message.id}
                    className={`rounded-lg border px-3.5 py-2.5 ${
                      message.is_internal
                        ? "border-amber-200 bg-amber-50/50"
                        : "border-slate-100 bg-white"
                    }`}
                  >
                    <div className="flex flex-wrap items-center gap-1.5 text-[10.5px]">
                      {message.is_internal ? (
                        <StickyNote className="h-3 w-3 text-amber-600" />
                      ) : (
                        <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                      )}
                      <span className="font-semibold text-slate-700">
                        {message.is_internal ? "Internal note" : message.author}
                      </span>
                      <span className="text-slate-400">· {formatDateTime(message.created_at)}</span>
                      {!message.is_internal ? (
                        <span className="ml-auto rounded-full bg-emerald-50 px-1.5 py-0.5 text-[9.5px] font-medium text-emerald-700 ring-1 ring-inset ring-emerald-200">
                          Approved
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-1.5 whitespace-pre-wrap text-[12.5px] leading-relaxed text-slate-600">
                      {message.body}
                    </p>
                  </div>
                ))
              )}
            </div>
          </section>
        </div>

        <aside className="space-y-4">
          <section className="card p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Ticket details</h3>
            <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-3">
              <KeyValue label="Status">
                <StatusBadge status={ticket.status} />
              </KeyValue>
              <KeyValue label="Priority">
                <PriorityBadge priority={ticket.priority} />
              </KeyValue>
              <KeyValue label="Category">
                <CategoryBadge category={ticket.category} />
              </KeyValue>
              <KeyValue label="Sentiment">
                <SentimentBadge sentiment={ticket.sentiment} />
              </KeyValue>
              <KeyValue label="Assignee">{ticket.assigned_to}</KeyValue>
              <KeyValue label="Channel">
                <span className="capitalize">{ticket.channel}</span>
              </KeyValue>
              <KeyValue label="Created">{formatDateTime(ticket.created_at)}</KeyValue>
              <KeyValue label="Updated">{formatDateTime(ticket.updated_at)}</KeyValue>
            </dl>
            <div className="mt-3 border-t border-slate-100 pt-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Analysis engine</p>
              <div className="mt-1.5">
                <EngineBadge
                  mode={ticket.ai_mode}
                  model={ticket.ai_mode === "llm" ? ticket.ai_model : "analyst v1"}
                />
              </div>
              <p className="mt-1.5 text-[10.5px] text-slate-400">
                Provider: {ticket.ai_provider || "built-in"}
              </p>
            </div>
          </section>

          <section
            className={`rounded-xl border p-4 shadow-card ${
              ticket.requires_human
                ? "border-amber-200 bg-amber-50/60"
                : "border-emerald-200 bg-emerald-50/50"
            }`}
          >
            <div className="flex items-center gap-2">
              {ticket.requires_human ? (
                <ShieldAlert className="h-4 w-4 text-amber-600" />
              ) : (
                <Zap className="h-4 w-4 text-emerald-600" />
              )}
              <h3
                className={`text-xs font-semibold uppercase tracking-wider ${
                  ticket.requires_human ? "text-amber-800" : "text-emerald-800"
                }`}
              >
                Recommended action
              </h3>
            </div>
            <p className={`mt-1.5 text-[13px] font-semibold ${ticket.requires_human ? "text-amber-900" : "text-emerald-900"}`}>
              {ticket.suggested_action}
            </p>
            {ticket.escalation_reason ? (
              <p className="mt-2 text-[11.5px] leading-relaxed text-amber-800">
                {ticket.escalation_reason}
              </p>
            ) : (
              <p className="mt-2 text-[11.5px] leading-relaxed text-emerald-800">
                No escalation trigger was found. Review the grounded draft and approve it if it looks right.
              </p>
            )}
          </section>

          <section className="card p-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Activity</h3>
              {ticket.events.length > 7 ? (
                <button
                  type="button"
                  className="inline-flex items-center gap-0.5 text-[10px] font-medium text-brand-600 hover:underline"
                  onClick={() => setShowAllEvents((value) => !value)}
                >
                  {showAllEvents ? "Less" : "All"}
                  <ChevronDown
                    className={`h-3 w-3 transition ${showAllEvents ? "rotate-180" : ""}`}
                  />
                </button>
              ) : null}
            </div>
            <ol className="mt-3 space-y-3">
              {events.map((event) => {
                const tone =
                  event.action === "resolved" || event.action === "approved"
                    ? "text-emerald-500"
                    : event.action === "escalated"
                      ? "text-rose-500"
                      : event.action === "guardrail" || event.action === "flagged"
                        ? "text-amber-500"
                        : "text-slate-400";
                return (
                  <li key={event.id} className="flex gap-2.5">
                    <CircleDot className={`mt-0.5 h-3 w-3 shrink-0 ${tone}`} />
                    <div className="min-w-0">
                      <p className="text-[11px] font-semibold text-slate-700">
                        {EVENT_LABEL[event.action] ?? event.action}
                      </p>
                      <p className="mt-0.5 text-[10.5px] leading-relaxed text-slate-500">{event.detail}</p>
                      <p className="mt-0.5 text-[9.5px] uppercase tracking-wide text-slate-400">
                        {event.actor} · {relativeTime(event.created_at)}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ol>
          </section>

          <p className="flex items-start gap-1.5 px-1 text-[10.5px] leading-relaxed text-slate-400">
            <Sparkles className="mt-0.5 h-3 w-3 shrink-0" />
            Drafts are generated only from the retrieved articles above. SupportPilot cannot see live order or
            payment systems.
          </p>
        </aside>
      </div>
    </div>
  );
}