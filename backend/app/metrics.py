"""Dashboard analytics computed from live ticket rows (never hardcoded)."""

from __future__ import annotations

from collections import Counter
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .domain import CATEGORIES, PRIORITIES, STATUSES, Category, Priority, Sentiment, TicketStatus
from .models import Ticket
from .serializers import ticket_summary
from .utils import utcnow

PRIORITY_RANK = {Priority.URGENT.value: 0, Priority.HIGH.value: 1, Priority.MEDIUM.value: 2, Priority.LOW.value: 3}


def compute_metrics(session: Session) -> dict:
    tickets = list(session.scalars(select(Ticket)).all())
    now = utcnow()

    status_counts = Counter(ticket.status for ticket in tickets)
    category_counts = Counter(ticket.category for ticket in tickets)
    priority_counts = Counter(ticket.priority for ticket in tickets)
    sentiment_counts = Counter(ticket.sentiment for ticket in tickets)

    awaiting_review = [
        ticket
        for ticket in tickets
        if ticket.requires_human and ticket.status != TicketStatus.RESOLVED.value
    ]
    resolved = [ticket for ticket in tickets if ticket.status == TicketStatus.RESOLVED.value]
    resolved_without_escalation = [ticket for ticket in resolved if not ticket.requires_human]
    escalated_total = status_counts.get(TicketStatus.ESCALATED.value, 0)

    total = len(tickets)
    avg_confidence = round(sum(ticket.confidence for ticket in tickets) / total * 100) if total else 0
    drafts = sum(1 for ticket in tickets if ticket.draft_reply)
    human_review_rate = round(len(awaiting_review) / total * 100) if total else 0
    resolve_rate = round(len(resolved) / total * 100) if total else 0

    awaiting_review.sort(
        key=lambda ticket: (PRIORITY_RANK.get(ticket.priority, 9), -(ticket.created_at.timestamp()))
    )
    recent = sorted(tickets, key=lambda ticket: ticket.created_at, reverse=True)[:6]

    trend = []
    for offset in range(6, -1, -1):
        day = (now - timedelta(days=offset)).date()
        created = sum(1 for ticket in tickets if _date(ticket.created_at) == day)
        resolved_that_day = sum(1 for ticket in resolved if ticket.resolved_at and _date(ticket.resolved_at) == day)
        trend.append({"date": day.isoformat(), "created": created, "resolved": resolved_that_day})

    totals: dict[str, int | float] = {
        "total": total,
        "open": total - len(resolved),
        "new": status_counts.get(TicketStatus.NEW.value, 0),
        "in_progress": status_counts.get(TicketStatus.IN_PROGRESS.value, 0),
        "escalated": escalated_total,
        "resolved": len(resolved),
        "awaiting_review": len(awaiting_review),
        "resolved_without_escalation": len(resolved_without_escalation),
        "resolved_with_escalation": len(resolved) - len(resolved_without_escalation),
        "drafts_generated": drafts,
        "avg_confidence": avg_confidence,
        "human_review_rate": human_review_rate,
        "resolve_rate": resolve_rate,
        "urgent": priority_counts.get(Priority.URGENT.value, 0),
    }

    return {
        "totals": totals,
        "by_category": _fill(category_counts, [category.value for category in CATEGORIES]),
        "by_priority": _fill(priority_counts, [priority.value for priority in PRIORITIES]),
        "by_status": _fill(status_counts, [status.value for status in STATUSES]),
        "by_sentiment": _fill(sentiment_counts, [sentiment.value for sentiment in Sentiment]),
        "trend": trend,
        "recent": [ticket_summary(ticket) for ticket in recent],
        "human_review": [ticket_summary(ticket) for ticket in awaiting_review[:5]],
    }


def _fill(counter: Counter[str], keys: list[str]) -> dict[str, int]:
    return {key: counter.get(key, 0) for key in keys}


def _date(value) -> object:  # type: ignore[no-untyped-def]
    return value.date() if hasattr(value, "date") else value