import { useEffect, useMemo, useState } from "react";
import { BookOpen, FileText, Search, X } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";

import {
  CategoryBadge,
  EmptyState,
  ErrorState,
  PageHeader,
  Skeleton,
} from "../components/ui";
import { api, errorMessage } from "../lib/api";
import { useDebounced } from "../lib/hooks";
import { CATEGORY_META, CATEGORY_ORDER } from "../lib/labels";
import type { KnowledgeListResponse } from "../lib/types";

export function KnowledgePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get("q") ?? "");
  const [category, setCategory] = useState(searchParams.get("category") ?? "");
  const [data, setData] = useState<KnowledgeListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const debouncedSearch = useDebounced(search, 250);
  const slug = searchParams.get("slug");

  useEffect(() => {
    let active = true;
    setLoading(true);
    api
      .knowledge({
        q: debouncedSearch.trim() || undefined,
        category: category || undefined,
      })
      .then((response) => {
        if (!active) return;
        setData(response);
        setError(null);
      })
      .catch((cause) => {
        if (!active) return;
        setError(errorMessage(cause));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [debouncedSearch, category]);

  const selected = useMemo(() => {
    if (!data) return null;
    return data.items.find((article) => article.slug === slug) ?? data.items[0] ?? null;
  }, [data, slug]);

  const selectArticle = (articleSlug: string) => {
    const next = new URLSearchParams(searchParams);
    next.set("slug", articleSlug);
    setSearchParams(next, { replace: true });
  };

  const clearSearch = () => {
    setSearch("");
    const next = new URLSearchParams(searchParams);
    next.delete("q");
    setSearchParams(next, { replace: true });
  };

  return (
    <div>
      <PageHeader
        title="Knowledge Base"
        subtitle="The single source of truth for every AI draft. If it is not here, the AI says so."
      >
        <span className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500">
          <BookOpen className="h-3.5 w-3.5" />
          {data?.total ?? "—"} articles · keyword retrieval
        </span>
      </PageHeader>

      <div className="grid gap-4 lg:grid-cols-[390px_minmax(0,1fr)] lg:items-start">
        <section className="card flex max-h-[calc(100vh-8rem)] flex-col overflow-hidden lg:sticky lg:top-6">
          <div className="space-y-2.5 border-b border-slate-100 p-3">
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
              <input
                className="input py-1.5 pl-8 pr-8 text-xs"
                placeholder="Search policies, FAQs and guides…"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                aria-label="Search knowledge base"
              />
              {search ? (
                <button
                  type="button"
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-slate-400 hover:text-slate-600"
                  onClick={clearSearch}
                  aria-label="Clear search"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              ) : null}
            </div>
            <div className="flex flex-wrap gap-1">
              <button
                type="button"
                onClick={() => setCategory("")}
                className={`rounded-full px-2 py-1 text-[10.5px] font-medium transition ${
                  category === ""
                    ? "bg-slate-900 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                All <span className="text-slate-400">{data?.total ?? 0}</span>
              </button>
              {CATEGORY_ORDER.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setCategory(category === item ? "" : item)}
                  className={`rounded-full px-2 py-1 text-[10.5px] font-medium transition ${
                    category === item
                      ? "bg-slate-900 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {CATEGORY_META[item].label}
                  <span className="ml-1 text-slate-400">{data?.by_category[item] ?? 0}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            {loading && !data ? (
              <div className="space-y-2 p-3">
                {[0, 1, 2, 3, 4].map((item) => (
                  <div key={item} className="space-y-1.5 rounded-lg border border-slate-100 p-3">
                    <Skeleton className="h-3 w-32" />
                    <Skeleton className="h-3 w-full" />
                    <Skeleton className="h-3 w-2/3" />
                  </div>
                ))}
              </div>
            ) : error ? (
              <div className="p-3">
                <ErrorState message={error} />
              </div>
            ) : data && data.items.length === 0 ? (
              <EmptyState
                icon={BookOpen}
                title="No articles found"
                description="Try a broader search term or choose a different category."
                action={
                  <button type="button" className="btn btn-secondary btn-sm" onClick={clearSearch}>
                    Clear search
                  </button>
                }
              />
            ) : (
              <div>
                {data?.items.map((article) => (
                  <button
                    key={article.slug}
                    type="button"
                    onClick={() => selectArticle(article.slug)}
                    className={`block w-full border-b border-slate-100 px-3.5 py-3 text-left transition ${
                      selected?.slug === article.slug ? "bg-brand-50/60" : "hover:bg-slate-50/80"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-[12.5px] font-semibold text-slate-800">{article.title}</p>
                      <CategoryBadge category={article.category} />
                    </div>
                    <p className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-slate-500">
                      {article.summary}
                    </p>
                    <p className="mt-1.5 text-[10px] uppercase tracking-wide text-slate-400">
                      {article.article_type}
                    </p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </section>

        <section className="min-w-0">
          {selected ? (
            <article className="card overflow-hidden">
              <div className="border-b border-slate-100 bg-slate-50/50 px-6 py-5">
                <div className="flex flex-wrap items-center gap-2">
                  <CategoryBadge category={selected.category} />
                  <span className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                    {selected.article_type}
                  </span>
                </div>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">
                  {selected.title}
                </h2>
                <p className="mt-1.5 max-w-3xl text-sm text-slate-500">{selected.summary}</p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {selected.tags.map((tag) => (
                    <span
                      key={tag}
                      className="rounded-full bg-white px-2 py-0.5 text-[10px] font-medium text-slate-500 ring-1 ring-inset ring-slate-200"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>

              <div className="px-6 py-5">
                <div className="space-y-3.5 text-[13.5px] leading-relaxed text-slate-700">
                  {selected.content.split("\n").filter(Boolean).map((paragraph, index) => (
                    <p key={index}>{paragraph}</p>
                  ))}
                </div>

                <div className="mt-6 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-4 text-[11px] text-slate-400">
                  <span className="flex items-center gap-1.5">
                    <FileText className="h-3.5 w-3.5" />
                    Retrieved by BM25 over title, tags, summary and body.
                  </span>
                  <Link
                    to={`/inbox?category=${selected.category}`}
                    className="font-medium text-brand-600 hover:underline"
                  >
                    View tickets in this category →
                  </Link>
                </div>
              </div>
            </article>
          ) : (
            <div className="card flex min-h-[440px] items-center justify-center">
              <EmptyState
                icon={BookOpen}
                title="Select an article"
                description="Browse the policies and guides that ground every AI-generated reply."
              />
            </div>
          )}
        </section>
      </div>
    </div>
  );
}