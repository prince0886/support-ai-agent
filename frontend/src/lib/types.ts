export type Category =
  | "billing"
  | "refund"
  | "shipping"
  | "technical_support"
  | "general_inquiry";

export type Priority = "low" | "medium" | "high" | "urgent";
export type TicketStatus = "new" | "in_progress" | "escalated" | "resolved";
export type DraftStatus = "draft" | "edited" | "approved";
export type Sentiment = "positive" | "neutral" | "frustrated" | "angry";
export type AiMode = "llm" | "fallback";

export interface TicketSummary {
  id: number;
  reference: string;
  customer_name: string;
  customer_email: string;
  subject: string;
  preview: string;
  channel: "email" | "chat" | "web" | "phone";
  category: Category;
  priority: Priority;
  status: TicketStatus;
  intent: string;
  sentiment: Sentiment;
  confidence: number;
  requires_human: boolean;
  risk_flags: string[];
  ai_mode: AiMode;
  draft_status: DraftStatus;
  assigned_to: string;
  created_at: string;
  updated_at: string;
}

export interface TicketSource {
  id: number;
  slug: string;
  title: string;
  category: Category;
  summary: string;
  score: number;
  excerpt: string;
}

export interface TicketMessage {
  id: number;
  role: "customer" | "assistant" | "note" | "system";
  author: string;
  body: string;
  is_internal: boolean;
  created_at: string;
}

export interface TicketEvent {
  id: number;
  action: string;
  detail: string;
  actor: string;
  created_at: string;
}

export interface TicketDetail extends TicketSummary {
  message: string;
  classification_reason: string;
  escalation_reason: string | null;
  suggested_action: string;
  draft_reply: string;
  approved_reply: string | null;
  approved_at: string | null;
  resolved_at: string | null;
  ai_provider: string;
  ai_model: string;
  sources: TicketSource[];
  messages: TicketMessage[];
  events: TicketEvent[];
}

export interface Facets {
  category: Record<string, number>;
  priority: Record<string, number>;
  status: Record<string, number>;
}

export interface TicketListResponse {
  items: TicketSummary[];
  total: number;
  facets: Facets;
}

export interface Metrics {
  totals: {
    total: number;
    open: number;
    new: number;
    in_progress: number;
    escalated: number;
    resolved: number;
    awaiting_review: number;
    resolved_without_escalation: number;
    resolved_with_escalation: number;
    drafts_generated: number;
    avg_confidence: number;
    human_review_rate: number;
    resolve_rate: number;
    urgent: number;
  };
  by_category: Record<Category, number>;
  by_priority: Record<Priority, number>;
  by_status: Record<TicketStatus, number>;
  by_sentiment: Record<Sentiment, number>;
  trend: Array<{ date: string; created: number; resolved: number }>;
  recent: TicketSummary[];
  human_review: TicketSummary[];
}

export interface AIStatus {
  enabled: boolean;
  configured: boolean;
  degraded: boolean;
  provider: string;
  model: string;
  mode: "llm" | "fallback";
  base_url_host: string;
  last_error: string | null;
  last_error_at: string | null;
  last_success_at: string | null;
  last_latency_ms: number | null;
  retry_in_seconds: number | null;
}

export interface SystemStatus {
  app_name: string;
  app_version: string;
  environment: string;
  demo_reset_enabled: boolean;
  retrieval_top_k: number;
  ai: AIStatus;
  counts: {
    tickets: number;
    articles: number;
    new: number;
    in_progress: number;
    escalated: number;
    resolved: number;
  };
}

export interface KnowledgeArticle {
  id: number;
  slug: string;
  title: string;
  category: Category;
  summary: string;
  content: string;
  tags: string[];
  article_type: string;
  updated_at: string;
}

export interface KnowledgeListResponse {
  items: KnowledgeArticle[];
  total: number;
  by_category: Record<Category, number>;
}

export interface KnowledgeSearchResponse {
  query: string;
  hits: Array<{
    slug: string;
    title: string;
    category: Category;
    summary: string;
    score: number;
    excerpt: string;
  }>;
}

export interface AITestResult {
  ok: boolean;
  detail: string;
  latency_ms: number | null;
  provider: string;
  model: string;
  mode: "llm" | "fallback";
}

export interface TicketFilters {
  q?: string;
  category?: Category | "";
  priority?: Priority | "";
  status?: TicketStatus | "";
  requires_human?: boolean;
  sort?: "newest" | "oldest" | "priority" | "updated";
  limit?: number;
}

export interface NewTicketInput {
  message: string;
  customer_name?: string;
  customer_email?: string;
  subject?: string;
  channel?: "email" | "chat" | "web" | "phone";
}