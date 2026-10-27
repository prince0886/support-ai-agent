import type {
  AITestResult,
  KnowledgeArticle,
  KnowledgeListResponse,
  KnowledgeSearchResponse,
  Metrics,
  NewTicketInput,
  SystemStatus,
  TicketDetail,
  TicketFilters,
  TicketListResponse,
  TicketStatus,
} from "./types";

const BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function describeError(payload: unknown, fallback: string): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          item && typeof item === "object" && "msg" in item
            ? String((item as { msg: unknown }).msg)
            : String(item),
        )
        .join(", ");
    }
  }
  return fallback;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
    });
  } catch {
    throw new ApiError(
      "Cannot reach the SupportPilot API. Is the backend running on port 8000?",
      0,
    );
  }

  const text = await response.text();
  let payload: unknown = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
  }

  if (!response.ok) {
    throw new ApiError(
      describeError(payload, `Request failed with status ${response.status}`),
      response.status,
    );
  }
  return payload as T;
}

function toQuery(params: Record<string, unknown>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

export const api = {
  metrics: () => request<Metrics>("/api/metrics"),

  status: () => request<SystemStatus>("/api/system/status"),

  testAi: () => request<AITestResult>("/api/system/ai/test", { method: "POST" }),

  resetDemo: () =>
    request<{ reset: boolean; tickets: number; articles: number }>("/api/system/demo/reset", {
      method: "POST",
    }),

  tickets: (filters: TicketFilters = {}) =>
    request<TicketListResponse>(`/api/tickets${toQuery({ ...filters })}`),

  ticket: (id: number | string) => request<TicketDetail>(`/api/tickets/${id}`),

  createTicket: (input: NewTicketInput) =>
    request<TicketDetail>("/api/tickets", {
      method: "POST",
      body: JSON.stringify(input),
    }),

  updateTicket: (
    id: number,
    patch: Partial<{
      status: TicketStatus;
      category: string;
      priority: string;
      escalation_reason: string;
      assigned_to: string;
    }>,
  ) =>
    request<TicketDetail>(`/api/tickets/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),

  saveDraft: (id: number, body: string) =>
    request<TicketDetail>(`/api/tickets/${id}/draft`, {
      method: "POST",
      body: JSON.stringify({ body }),
    }),

  approve: (id: number, body?: string, note?: string) =>
    request<TicketDetail>(`/api/tickets/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ body: body ?? null, note: note ?? null }),
    }),

  resolve: (id: number, body?: string, note?: string) =>
    request<TicketDetail>(`/api/tickets/${id}/resolve`, {
      method: "POST",
      body: JSON.stringify({ body: body ?? null, note: note ?? null }),
    }),

  escalate: (id: number, reason: string) =>
    request<TicketDetail>(`/api/tickets/${id}/escalate`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),

  reopen: (id: number, note?: string) =>
    request<TicketDetail>(`/api/tickets/${id}/reopen`, {
      method: "POST",
      body: JSON.stringify({ note: note ?? null }),
    }),

  addMessage: (id: number, body: string, internal: boolean) =>
    request<TicketDetail>(`/api/tickets/${id}/messages`, {
      method: "POST",
      body: JSON.stringify({ body, internal }),
    }),

  reanalyze: (id: number) =>
    request<TicketDetail>(`/api/tickets/${id}/reanalyze`, { method: "POST" }),

  knowledge: (params: { q?: string; category?: string } = {}) =>
    request<KnowledgeListResponse>(`/api/knowledge${toQuery(params)}`),

  article: (slug: string) => request<KnowledgeArticle>(`/api/knowledge/${slug}`),

  searchKnowledge: (query: string, topK = 3) =>
    request<KnowledgeSearchResponse>("/api/knowledge/search", {
      method: "POST",
      body: JSON.stringify({ query, top_k: topK }),
    }),
};

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong.";
}