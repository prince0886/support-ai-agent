"""ORM -> API payload conversion."""

from __future__ import annotations

import re

from .models import KnowledgeArticle, Ticket
from .utils import iso


def preview(text: str, limit: int = 160) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1].rsplit(" ", 1)[0] + "…"


def ticket_summary(ticket: Ticket) -> dict:
    return {
        "id": ticket.id,
        "reference": ticket.reference,
        "customer_name": ticket.customer_name,
        "customer_email": ticket.customer_email,
        "subject": ticket.subject,
        "preview": preview(ticket.message),
        "channel": ticket.channel,
        "category": ticket.category,
        "priority": ticket.priority,
        "status": ticket.status,
        "intent": ticket.intent,
        "sentiment": ticket.sentiment,
        "confidence": round(ticket.confidence, 2),
        "requires_human": ticket.requires_human,
        "risk_flags": list(ticket.risk_flags or []),
        "ai_mode": ticket.ai_mode,
        "draft_status": ticket.draft_status,
        "assigned_to": ticket.assigned_to,
        "created_at": iso(ticket.created_at),
        "updated_at": iso(ticket.updated_at),
    }


def ticket_detail(ticket: Ticket) -> dict:
    payload = ticket_summary(ticket)
    payload.update(
        {
            "message": ticket.message,
            "classification_reason": ticket.classification_reason,
            "escalation_reason": ticket.escalation_reason,
            "suggested_action": ticket.suggested_action,
            "draft_reply": ticket.draft_reply,
            "approved_reply": ticket.approved_reply,
            "approved_at": iso(ticket.approved_at),
            "resolved_at": iso(ticket.resolved_at),
            "ai_provider": ticket.ai_provider,
            "ai_model": ticket.ai_model,
            "sources": [
                {
                    "id": source.article.id if source.article else source.article_id,
                    "slug": source.article.slug if source.article else "",
                    "title": source.article.title if source.article else "",
                    "category": source.article.category if source.article else "",
                    "summary": source.article.summary if source.article else "",
                    "score": round(source.score, 3),
                    "excerpt": source.excerpt,
                }
                for source in ticket.sources
            ],
            "messages": [
                {
                    "id": message.id,
                    "role": message.role,
                    "author": message.author,
                    "body": message.body,
                    "is_internal": message.is_internal,
                    "created_at": iso(message.created_at),
                }
                for message in ticket.messages
            ],
            "events": [
                {
                    "id": event.id,
                    "action": event.action,
                    "detail": event.detail,
                    "actor": event.actor,
                    "created_at": iso(event.created_at),
                }
                for event in ticket.events
            ],
        }
    )
    return payload


def article_out(article: KnowledgeArticle) -> dict:
    return {
        "id": article.id,
        "slug": article.slug,
        "title": article.title,
        "category": article.category,
        "summary": article.summary,
        "content": article.content,
        "tags": list(article.tags or []),
        "article_type": article.article_type,
        "updated_at": iso(article.updated_at),
    }