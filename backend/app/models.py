"""SQLAlchemy models for tickets, knowledge articles and audit trail."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .domain import DraftStatus, MessageRole, TicketStatus
from .utils import utcnow


class KnowledgeArticle(Base):
    __tablename__ = "knowledge_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(40), index=True)
    summary: Mapped[str] = mapped_column(String(400))
    content: Mapped[str] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    article_type: Mapped[str] = mapped_column(String(32), default="faq")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    sources: Mapped[list["TicketSource"]] = relationship(back_populates="article")


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    customer_name: Mapped[str] = mapped_column(String(120))
    customer_email: Mapped[str] = mapped_column(String(190))
    channel: Mapped[str] = mapped_column(String(20), default="email")
    subject: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)

    status: Mapped[str] = mapped_column(String(20), default=TicketStatus.NEW.value, index=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    priority: Mapped[str] = mapped_column(String(20), index=True)
    intent: Mapped[str] = mapped_column(String(200), default="")
    sentiment: Mapped[str] = mapped_column(String(20), default="neutral")
    classification_reason: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    risk_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    requires_human: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    escalation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_action: Mapped[str] = mapped_column(String(120), default="")

    draft_reply: Mapped[str] = mapped_column(Text, default="")
    draft_status: Mapped[str] = mapped_column(String(20), default=DraftStatus.DRAFT.value)
    approved_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    ai_mode: Mapped[str] = mapped_column(String(16), default="fallback")
    ai_provider: Mapped[str] = mapped_column(String(60), default="")
    ai_model: Mapped[str] = mapped_column(String(120), default="")
    assigned_to: Mapped[str] = mapped_column(String(120), default="Unassigned")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sources: Mapped[list["TicketSource"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketSource.rank",
    )
    messages: Mapped[list["TicketMessage"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketMessage.created_at",
    )
    events: Mapped[list["TicketEvent"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketEvent.created_at",
    )


class TicketSource(Base):
    """A knowledge article retrieved for a ticket, with the excerpt used."""

    __tablename__ = "ticket_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), index=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("knowledge_articles.id", ondelete="CASCADE"))
    rank: Mapped[int] = mapped_column(Integer, default=1)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    excerpt: Mapped[str] = mapped_column(Text, default="")

    ticket: Mapped[Ticket] = relationship(back_populates="sources")
    article: Mapped[KnowledgeArticle] = relationship(back_populates="sources")


class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), default=MessageRole.CUSTOMER.value)
    author: Mapped[str] = mapped_column(String(120), default="Customer")
    body: Mapped[str] = mapped_column(Text)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    ticket: Mapped[Ticket] = relationship(back_populates="messages")


class TicketEvent(Base):
    """Audit trail of every automated and human action on a ticket."""

    __tablename__ = "ticket_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(60))
    detail: Mapped[str] = mapped_column(Text, default="")
    actor: Mapped[str] = mapped_column(String(60), default="SupportPilot")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    ticket: Mapped[Ticket] = relationship(back_populates="events")