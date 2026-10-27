"""Request and response models for the REST API."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from .domain import Category, Priority, TicketStatus


class TicketCreate(BaseModel):
    message: str = Field(min_length=3, max_length=8000)
    customer_name: str | None = Field(default=None, max_length=120)
    customer_email: str | None = Field(default=None, max_length=190)
    subject: str | None = Field(default=None, max_length=200)
    channel: str = Field(default="email", pattern="^(email|chat|web|phone)$")

    @field_validator("customer_name", "customer_email", "subject", mode="before")
    @classmethod
    def _strip(cls, value: object) -> str | None:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return None

    @field_validator("message")
    @classmethod
    def _message(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise ValueError("message must contain at least 3 characters")
        return cleaned


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    category: Category | None = None
    priority: Priority | None = None
    escalation_reason: str | None = Field(default=None, max_length=2000)
    assigned_to: str | None = Field(default=None, max_length=120)


class DraftUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=8000)

    @field_validator("body")
    @classmethod
    def _body(cls, value: str) -> str:
        return value.strip()


class ApproveRequest(BaseModel):
    body: str | None = Field(default=None, max_length=8000)
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("body", "note", mode="before")
    @classmethod
    def _strip(cls, value: object) -> str | None:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return None


class ResolveRequest(BaseModel):
    body: str | None = Field(default=None, max_length=8000)
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("body", "note", mode="before")
    @classmethod
    def _strip(cls, value: object) -> str | None:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return None


class EscalateRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)

    @field_validator("reason")
    @classmethod
    def _reason(cls, value: str) -> str:
        return value.strip()


class ReopenRequest(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=8000)
    internal: bool = False

    @field_validator("body")
    @classmethod
    def _body(cls, value: str) -> str:
        return value.strip()


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=3, ge=1, le=10)


class TicketSourceOut(BaseModel):
    id: int
    slug: str
    title: str
    category: str
    summary: str
    score: float
    excerpt: str


class TicketMessageOut(BaseModel):
    id: int
    role: str
    author: str
    body: str
    is_internal: bool
    created_at: str


class TicketEventOut(BaseModel):
    id: int
    action: str
    detail: str
    actor: str
    created_at: str


class TicketSummary(BaseModel):
    id: int
    reference: str
    customer_name: str
    customer_email: str
    subject: str
    preview: str
    channel: str
    category: str
    priority: str
    status: str
    intent: str
    sentiment: str
    confidence: float
    requires_human: bool
    risk_flags: list[str]
    ai_mode: str
    draft_status: str
    assigned_to: str
    created_at: str
    updated_at: str


class TicketDetail(TicketSummary):
    message: str
    classification_reason: str
    escalation_reason: str | None
    suggested_action: str
    draft_reply: str
    approved_reply: str | None
    approved_at: str | None
    resolved_at: str | None
    ai_provider: str
    ai_model: str
    sources: list[TicketSourceOut]
    messages: list[TicketMessageOut]
    events: list[TicketEventOut]


class TicketListResponse(BaseModel):
    items: list[TicketSummary]
    total: int
    facets: dict[str, dict[str, int]]


class KnowledgeArticleOut(BaseModel):
    id: int
    slug: str
    title: str
    category: str
    summary: str
    content: str
    tags: list[str]
    article_type: str
    updated_at: str


class KnowledgeListResponse(BaseModel):
    items: list[KnowledgeArticleOut]
    total: int
    by_category: dict[str, int]


class KnowledgeSearchHit(BaseModel):
    slug: str
    title: str
    category: str
    summary: str
    score: float
    excerpt: str


class KnowledgeSearchResponse(BaseModel):
    query: str
    hits: list[KnowledgeSearchHit]


class MetricsResponse(BaseModel):
    totals: dict[str, int | float]
    by_category: dict[str, int]
    by_priority: dict[str, int]
    by_status: dict[str, int]
    by_sentiment: dict[str, int]
    trend: list[dict[str, int | str]]
    recent: list[TicketSummary]
    human_review: list[TicketSummary]


class AIStatus(BaseModel):
    enabled: bool
    configured: bool
    degraded: bool = False
    provider: str
    model: str
    mode: str
    base_url_host: str
    last_error: str | None = None
    last_error_at: str | None = None
    last_success_at: str | None = None
    last_latency_ms: int | None = None
    retry_in_seconds: int | None = None


class SystemStatusResponse(BaseModel):
    app_name: str
    app_version: str
    environment: str
    demo_reset_enabled: bool
    retrieval_top_k: int
    ai: AIStatus
    counts: dict[str, int]


class AITestResponse(BaseModel):
    ok: bool
    detail: str
    latency_ms: int | None = None
    provider: str
    model: str
    mode: str


class DemoResetResponse(BaseModel):
    reset: bool
    tickets: int
    articles: int


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str