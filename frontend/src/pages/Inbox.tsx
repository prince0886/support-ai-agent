import { useEffect, useMemo, useState } from "react";
import {
  ArrowDownUp,
  BookOpen,
  Filter,
  Inbox,
  Plus,
  Search,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { useSearchParams } from "react-router-dom";

import { useNewTicket } from "../components/NewTicketModal";
import { TicketListItem, TicketListSkeleton } from "../components/TicketList";
import { TicketDetailPanel } from "../components/TicketDetail";
import { EmptyState, ErrorState, PageHeader } from "../components/ui";
import { useDebounced, useTicketList } from "../lib/hooks";
import {
  CATEGORY_META,
  CATEGORY_ORDER,
  PRIORITY_META,
  PRIORITY_ORDER,
  STATUS_META,
} from "../lib/labels";
import type { Category, Priority, TicketStatus } from "../lib/types";
import { useApp } from "../store/AppStore";
import { useParams } from "react-router-dom";

const STATUS_TABS: Array<{ value: TicketStatus | ""; label: string }> = [
  { value: "", label: "All" },
  { value: "new", label: "New" },
  { value: "in_progress", label: "In progress" },
  { value: "escalated", label: "Escalated" },
  { value: "resolved", label: "Resolved" },
];

export function InboxPage() {
  const { id } = useParams<{ id: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const { refresh } = useApp();
  const { open } = useNewTicket();

  const q = searchParams.get("q") ?? "";
  const status = (searchParams.get("status") ?? "") as TicketStatus | "";
  const category = (searchParams.get("category") ?? "") as Category | "";
  const priority = (searchParams.get("priority") ?? "") as Priority | "";
  const humanOnly = searchParams.get("requires_human") === "true";
  const sort = (searchParams.get("sort") ?? "newest") as
    | "newest"
    | "oldest"
    | "priority"
    | "updated";

  const [searchText, setSearchText] = useState(q);
  const debouncedSearch = useDebounced(searchText, 250);

  const filters = useMemo(
    () => ({
      q: q || undefined,
      status: status || undefined,
      category: category || undefined,
      priority: priority || undefined,
      requires_human: humanOnly || undefined,
      sort,
      limit: 100,
    }),
    [q, status, category, priority, humanOnly, sort],
  );

  const { data, loading, error, reload } = useTicketList(filters);

  useEffect(() => {
    if (debouncedSearch === q) return;
    const next = new URLSearchParams(searchParams);
    if (debouncedSearch.trim()) next.set("q", debouncedSearch.trim());
    else next.delete("q");
    setSearchParams(next, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch]);

  useEffect(() => {
    setSearchText(q);
  }, [q]);

  const updateParam = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next, { replace: true });
  };

  const clearFilters = () => {
    setSearchText("");
    setSearchParams(new URLSearchParams(), { replace: true });
  };

  const hasFilters = Boolean(q || status || category || priority || humanOnly || sort !== "newest");
  const selectedId = id ? Number(id) : null;
  const activeCount = data?.total ?? 0;

  const handleChanged = () => {
    void reload();
    void refresh();
  };

  return (
    <div>
      <PageHeader
        title="Support Inbox"
        subtitle="Every query, classified and drafted. Humans make the final call."
      >
        <button type="button" className="btn btn-primary" onClick={open}>
          <Plus className="h-4 w-4" />
          New ticket
        </button>
      </PageHeader>

      <div className="grid gap-4 lg:grid-cols-[370px_minmax(0,1fr)] lg:items-start">
        <section className="card flex max-h-[calc(100vh-8rem)] flex-col overflow-hidden lg:sticky lg:top-6">
          <div className="space-y-3 border-b border-slate-100 px-3.5 py-3">
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
              <input
                className="input py-1.5 pl-8 pr-8 text-xs"
                placeholder="Search by customer, subject or reference…"
                value={searchText}
                onChange={(event) => setSearchText(event.target.value)}
                aria-label="Search tickets"
              />
              {searchText ? (
                <button
                  type="button"
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-slate-400 hover:text-slate-600"
                  onClick={() => setSearchText("")}
                  aria-label="Clear search"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              ) : null}
            </div>

            <div className="flex flex-wrap gap-1">
              {STATUS_TABS.map((tab) => {
                const count = tab.value
                  ? data?.facets.status[tab.value] ?? 0
                  : data?.total ?? 0;
                const active = status === tab.value;
                return (
                  <button
                    key={tab.label}
                    type="button"
                    onClick={() => updateParam("status", tab.value)}
                    className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-[10.5px] font-medium transition ${
                      active
                        ? "bg-slate-900 text-white"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                  >
                    {tab.label}
                    <span className={active ? "text-slate-300" : "text-slate-400"}>{count}</span>
                  </button>
                );
              })}
            </div>

            <div className="grid grid-cols-2 gap-1.5">
              <select
                className="input px-2 py-1.5 text-[11px]"
                value={category}
                onChange={(event) => updateParam("category", event.target.value)}
                aria-label="Filter by category"
              >
                <option value="">All categories</option>
                {CATEGORY_ORDER.map((item) => (
                  <option key={item} value={item}>
                    {CATEGORY_META[item].label}
                  </option>
                ))}
              </select>
              <select
                className="input px-2 py-1.5 text-[11px]"
                value={priority}
                onChange={(event) => updateParam("priority", event.target.value)}
                aria-label="Filter by priority"
              >
                <option value="">All priorities</option>
                {PRIORITY_ORDER.map((item) => (
                  <option key={item} value={item}>
                    {PRIORITY_META[item].label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center justify-between gap-2">
              <button
                type="button"
                onClick={() =>
                  humanOnly ? updateParam("requires_human", "") : updateParam("requires_human", "true")
                }
                className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-[10.5px] font-medium ring-1 ring-inset transition ${
                  humanOnly
                    ? "bg-amber-100 text-amber-800 ring-amber-300"
                    : "bg-white text-slate-600 ring-slate-200 hover:bg-amber-50"
                }`}
              >
                <ShieldAlert className="h-3 w-3" />
                Needs human
              </button>

              <label className="flex items-center gap-1 text-[10.5px] text-slate-500">
                <ArrowDownUp className="h-3 w-3" />
                <select
                  className="rounded-md border-0 bg-transparent py-0 pl-1 pr-5 text-[10.5px] font-medium text-slate-600 focus:ring-0"
                  value={sort}
                  onChange={(event) => updateParam("sort", event.target.value)}
                  aria-label="Sort tickets"
                >
                  <option value="newest">Newest</option>
                  <option value="oldest">Oldest</option>
                  <option value="priority">Priority</option>
                  <option value="updated">Recently updated</option>
                </select>
              </label>
            </div>

            <div className="flex items-center justify-between text-[10.5px] text-slate-400">
              <span>
                {loading ? "Loading…" : `${activeCount} ticket${activeCount === 1 ? "" : "s"}`}
              </span>
              {hasFilters ? (
                <button
                  type="button"
                  onClick={clearFilters}
                  className="inline-flex items-center gap-1 font-medium text-brand-600 hover:underline"
                >
                  <Filter className="h-3 w-3" /> Clear filters
                </button>
              ) : null}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            {loading && !data ? (
              <TicketListSkeleton />
            ) : error ? (
              <div className="p-3">
                <ErrorState message={error} onRetry={() => void reload()} />
              </div>
            ) : data && data.items.length === 0 ? (
              <EmptyState
                icon={Inbox}
                title="No tickets match"
                description="Try a different search or clear the filters to see the full queue."
                action={
                  <button type="button" className="btn btn-secondary btn-sm" onClick={clearFilters}>
                    Clear filters
                  </button>
                }
              />
            ) : (
              <div>
                {data?.items.map((ticket) => (
                  <TicketListItem
                    key={ticket.id}
                    ticket={ticket}
                    selected={ticket.id === selectedId}
                  />
                ))}
              </div>
            )}
          </div>
        </section>

        <section className="min-w-0">
          {selectedId ? (
            <TicketDetailPanel
              key={selectedId}
              ticketId={selectedId}
              onChanged={handleChanged}
            />
          ) : (
            <div className="card flex min-h-[440px] items-center justify-center p-6">
              <div className="max-w-md text-center">
                <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-full bg-slate-100 text-slate-500">
                  <Inbox className="h-5 w-5" />
                </div>
                <p className="mt-3 text-sm font-semibold text-slate-800">Select a ticket</p>
                <p className="mt-1 text-sm text-slate-500">
                  Open any ticket to review the AI analysis, the retrieved policy and the draft before a
                  human sends it.
                </p>
                <div className="mt-5 grid grid-cols-3 gap-2 text-left">
                  {[
                    { icon: Sparkles, label: "Classification", hint: "Category, priority, intent" },
                    { icon: BookOpen, label: "Grounding", hint: "Article + excerpt" },
                    { icon: ShieldCheck, label: "Control", hint: "Approve, escalate, resolve" },
                  ].map((item) => (
                    <div key={item.label} className="rounded-lg border border-slate-100 bg-slate-50/60 p-2.5">
                      <item.icon className="h-3.5 w-3.5 text-brand-500" />
                      <p className="mt-1.5 text-[11px] font-semibold text-slate-700">{item.label}</p>
                      <p className="mt-0.5 text-[10px] leading-snug text-slate-500">{item.hint}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}