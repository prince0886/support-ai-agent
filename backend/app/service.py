"""Ticket use-cases: creation with AI analysis, filtering and human actions."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from .analysis import AnalysisResult, SupportAnalyst
from .domain import ALLOWED_TRANSITIONS, DraftStatus, MessageRole, Priority, TicketStatus
from .models import KnowledgeArticle, Ticket, TicketEvent, TicketMessage, TicketSource
from .schemas import TicketCreate, TicketUpdate
from .utils import iso, utcnow

logger = logging.getLogger(__name__)

PRIORITY_SORT = case(
    (Ticket.priority == Priority.URGENT.value, 0),
    (Ticket.priority == Priority.HIGH.value, 1),
    (Ticket.priority == Priority.MEDIUM.value, 2),
    else_=3,
)


class TicketNotFound(Exception):
    pass


class InvalidTransition(Exception):
    pass


def ticket_query():
    return select(Ticket).options(
        selectinload(Ticket.sources).selectinload(TicketSource.article),
        selectinload(Ticket.messages),
        selectinload(Ticket.events),
    )


def get_ticket(session: Session, ticket_id: int) -> Ticket:
    ticket = session.scalars(ticket_query().where(Ticket.id == ticket_id)).first()
    if ticket is None:
        raise TicketNotFound(f"Ticket {ticket_id} does not exist")
    return ticket


def _log(ticket: Ticket, action: str, detail: str, *, actor: str = "SupportPilot", at: datetime | None = None) -> None:
    ticket.events.append(TicketEvent(action=action, detail=detail, actor=actor, created_at=at or utcnow()))


def _derive_subject(message: str, intent: str, fallback: str | None) -> str:
    if fallback:
        return fallback[:200]
    first_sentence = message.strip().split("\n")[0]
    first_sentence = first_sentence.split(". ")[0].strip().rstrip(".")
    if len(first_sentence) > 72:
        first_sentence = first_sentence[:69].rsplit(" ", 1)[0] + "…"
    return first_sentence or intent or "New support request"


def apply_analysis(ticket: Ticket, result: AnalysisResult) -> None:
    ticket.category = result.category.value
    ticket.priority = result.priority.value
    ticket.intent = result.intent[:200]
    ticket.sentiment = result.sentiment.value
    ticket.classification_reason = result.classification_reason
    ticket.confidence = result.confidence
    ticket.risk_flags = result.risk_flags
    ticket.requires_human = result.requires_human
    ticket.escalation_reason = result.escalation_reason
    ticket.suggested_action = result.suggested_action
    ticket.draft_reply = result.draft_reply
    ticket.draft_status = DraftStatus.DRAFT.value
    ticket.ai_mode = result.ai_mode
    ticket.ai_provider = result.ai_provider
    ticket.ai_model = result.ai_model

    ticket.sources.clear()
    for rank, hit in enumerate(result.retrieved, start=1):
        ticket.sources.append(
            TicketSource(
                article_id=hit.article.id,
                rank=rank,
                score=hit.normalized_score,
                excerpt=hit.excerpt,
            )
        )

    if result.guardrail_notes:
        _log(
            ticket,
            "guardrail",
            " ".join(result.guardrail_notes),
            actor="Safety guardrail",
        )


async def create_ticket(
    session: Session,
    analyst: SupportAnalyst,
    payload: TicketCreate,
    *,
    use_llm: bool = True,
    created_at: datetime | None = None,
) -> Ticket:
    now = created_at or utcnow()
    customer_name = payload.customer_name or "Guest customer"
    articles = list(session.scalars(select(KnowledgeArticle)).all())

    ticket = Ticket(
        reference="pending",
        customer_name=customer_name,
        customer_email=payload.customer_email or "",
        channel=payload.channel,
        subject="pending",
        message=payload.message,
        status=TicketStatus.NEW.value,
        category="general_inquiry",
        priority=Priority.LOW.value,
        intent="",
        draft_reply="",
        created_at=now,
        updated_at=now,
    )
    session.add(ticket)
    session.flush()

    ticket.reference = f"SP-{1000 + ticket.id}"

    if use_llm:
        result = await analyst.analyze(
            message=payload.message,
            customer_name=customer_name,
            articles=articles,
        )
    else:
        result = analyst.analyze_deterministic(
            message=payload.message,
            customer_name=customer_name,
            articles=articles,
        )

    apply_analysis(ticket, result)
    ticket.subject = _derive_subject(payload.message, result.intent, payload.subject)
    # Keep backdated demo seeds honest instead of letting the UPDATE trigger
    # stamp the real wall-clock time.
    ticket.updated_at = now

    ticket.messages.append(
        TicketMessage(
            role=MessageRole.CUSTOMER.value,
            author=customer_name,
            body=payload.message,
            is_internal=False,
            created_at=now,
        )
    )

    engine_label = "LLM" if result.ai_mode == "llm" else "deterministic analyst"
    _log(
        ticket,
        "created",
        f"Received via {payload.channel}. Analyzed by the {engine_label} as "
        f"{result.category.label} / {result.priority.value} ({result.confidence:.0%} confidence).",
        at=now,
    )
    if result.requires_human:
        _log(
            ticket,
            "flagged",
            "Flagged for human review: " + (result.escalation_reason or "manual review required"),
            at=now,
        )

    session.commit()
    return get_ticket(session, ticket.id)


async def reanalyze_ticket(
    session: Session,
    analyst: SupportAnalyst,
    ticket: Ticket,
    *,
    use_llm: bool = True,
) -> Ticket:
    articles = list(session.scalars(select(KnowledgeArticle)).all())
    if use_llm:
        result = await analyst.analyze(
            message=ticket.message,
            customer_name=ticket.customer_name,
            articles=articles,
        )
    else:
        result = analyst.analyze_deterministic(
            message=ticket.message,
            customer_name=ticket.customer_name,
            articles=articles,
        )

    previous_draft_status = ticket.draft_status
    apply_analysis(ticket, result)
    if previous_draft_status == DraftStatus.APPROVED.value and ticket.approved_reply:
        ticket.draft_reply = ticket.approved_reply
    ticket.updated_at = utcnow()

    engine_label = "LLM" if result.ai_mode == "llm" else "deterministic analyst"
    _log(
        ticket,
        "reanalyzed",
        f"Re-analyzed by the {engine_label}: {result.category.label} / {result.priority.value}. "
        f"Suggested action: {result.suggested_action.lower()}.",
        actor="Human agent",
    )
    session.commit()
    return get_ticket(session, ticket.id)


def update_ticket(session: Session, ticket: Ticket, payload: TicketUpdate) -> Ticket:
    changes: list[str] = []
    actor = "Human agent"

    if payload.status is not None:
        new_status = ticket.status if isinstance(ticket.status, TicketStatus) else TicketStatus(ticket.status)
        allowed = ALLOWED_TRANSITIONS[new_status]
        if payload.status not in allowed:
            raise InvalidTransition(f"Cannot move a ticket from {new_status.value} to {payload.status.value}")
        if payload.status.value != ticket.status:
            changes.append(f"status {ticket.status} → {payload.status.value}")
            ticket.status = payload.status.value
            if payload.status is TicketStatus.RESOLVED:
                ticket.resolved_at = utcnow()
            elif ticket.resolved_at is not None:
                ticket.resolved_at = None

    if payload.category is not None and payload.category.value != ticket.category:
        changes.append(f"category {ticket.category} → {payload.category.value}")
        ticket.category = payload.category.value

    if payload.priority is not None and payload.priority.value != ticket.priority:
        changes.append(f"priority {ticket.priority} → {payload.priority.value}")
        ticket.priority = payload.priority.value

    if payload.escalation_reason is not None:
        ticket.escalation_reason = payload.escalation_reason
        changes.append("escalation reason updated")

    if payload.assigned_to is not None and payload.assigned_to != ticket.assigned_to:
        changes.append(f"assigned to {payload.assigned_to}")
        ticket.assigned_to = payload.assigned_to

    if changes:
        ticket.updated_at = utcnow()
        _log(ticket, "updated", "; ".join(changes).capitalize(), actor=actor)
        session.commit()
    return get_ticket(session, ticket.id)


def save_draft(session: Session, ticket: Ticket, body: str) -> Ticket:
    if ticket.status == TicketStatus.RESOLVED.value:
        raise ValueError("Cannot edit a draft on a resolved ticket. Reopen it first.")
    ticket.draft_reply = body.strip()
    ticket.draft_status = DraftStatus.EDITED.value
    ticket.updated_at = utcnow()
    _log(ticket, "draft_edited", "Human agent edited the AI draft.", actor="Human agent")
    session.commit()
    return get_ticket(session, ticket.id)


def approve_reply(session: Session, ticket: Ticket, body: str | None, note: str | None = None) -> Ticket:
    # A closed ticket is immutable until it is explicitly reopened, otherwise a
    # late approval silently overwrites the agreed reply and pollutes the audit
    # trail with a reply that was never sent.
    if ticket.status == TicketStatus.RESOLVED.value:
        raise ValueError("Cannot approve a reply on a resolved ticket. Reopen it first.")

    reply = (body or ticket.draft_reply or "").strip()
    if not reply:
        raise ValueError("There is no draft to approve")

    now = utcnow()
    ticket.approved_reply = reply
    ticket.approved_at = now
    ticket.draft_status = DraftStatus.APPROVED.value
    ticket.draft_reply = reply
    ticket.updated_at = now
    if ticket.status in {TicketStatus.NEW.value, TicketStatus.IN_PROGRESS.value}:
        ticket.status = TicketStatus.IN_PROGRESS.value

    ticket.messages.append(
        TicketMessage(
            role=MessageRole.ASSISTANT.value,
            author="Agent Rhea",
            body=reply,
            is_internal=False,
            created_at=now,
        )
    )
    _log(
        ticket,
        "approved",
        "Reply approved and recorded as sent. (Demo: no email provider is connected, so delivery is simulated.)",
        actor="Human agent",
        at=now,
    )
    if note:
        ticket.messages.append(
            TicketMessage(
                role=MessageRole.NOTE.value,
                author="Agent Rhea",
                body=note,
                is_internal=True,
                created_at=now,
            )
        )
    session.commit()
    return get_ticket(session, ticket.id)


def resolve_ticket(session: Session, ticket: Ticket, body: str | None, note: str | None) -> Ticket:
    # The note is owned by resolve_ticket below; passing it into approve_reply
    # as well would append the same internal note twice.
    if body and body.strip() and body.strip() != (ticket.approved_reply or ""):
        approve_reply(session, ticket, body)
        ticket = get_ticket(session, ticket.id)

    ticket.status = TicketStatus.RESOLVED.value
    ticket.resolved_at = utcnow()
    ticket.updated_at = ticket.resolved_at
    _log(ticket, "resolved", "Ticket marked resolved by a human agent.", actor="Human agent")
    if note:
        ticket.messages.append(
            TicketMessage(
                role=MessageRole.NOTE.value,
                author="Agent Rhea",
                body=note,
                is_internal=True,
                created_at=utcnow(),
            )
        )
    session.commit()
    return get_ticket(session, ticket.id)


def escalate_ticket(session: Session, ticket: Ticket, reason: str) -> Ticket:
    ticket.status = TicketStatus.ESCALATED.value
    ticket.escalation_reason = reason
    ticket.requires_human = True
    ticket.resolved_at = None
    ticket.updated_at = utcnow()
    _log(ticket, "escalated", f"Escalated to a human specialist: {reason}", actor="Human agent")
    session.commit()
    return get_ticket(session, ticket.id)


def reopen_ticket(session: Session, ticket: Ticket, note: str | None) -> Ticket:
    ticket.status = TicketStatus.IN_PROGRESS.value
    ticket.resolved_at = None
    ticket.updated_at = utcnow()
    _log(ticket, "reopened", note or "Ticket reopened by a human agent.", actor="Human agent")
    session.commit()
    return get_ticket(session, ticket.id)


def add_message(session: Session, ticket: Ticket, body: str, *, internal: bool) -> Ticket:
    now = utcnow()
    ticket.messages.append(
        TicketMessage(
            role=(MessageRole.NOTE.value if internal else MessageRole.ASSISTANT.value),
            author="Agent Rhea",
            body=body,
            is_internal=internal,
            created_at=now,
        )
    )
    ticket.updated_at = now
    _log(
        ticket,
        "note_added" if internal else "reply_sent",
        "Internal note added." if internal else "Agent reply recorded as sent.",
        actor="Human agent",
        at=now,
    )
    session.commit()
    return get_ticket(session, ticket.id)


def list_tickets(
    session: Session,
    *,
    search: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    requires_human: bool | None = None,
    sort: str = "newest",
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Ticket], int, dict[str, dict[str, int]]]:
    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Ticket.customer_name.ilike(pattern),
                Ticket.customer_email.ilike(pattern),
                Ticket.subject.ilike(pattern),
                Ticket.message.ilike(pattern),
                Ticket.reference.ilike(pattern),
            )
        )
    if category:
        filters.append(Ticket.category == category)
    if priority:
        filters.append(Ticket.priority == priority)
    if status:
        filters.append(Ticket.status == status)
    if requires_human is not None:
        filters.append(Ticket.requires_human == requires_human)

    total = session.scalar(select(func.count()).select_from(Ticket).where(*filters)) or 0

    query = ticket_query().where(*filters)
    if sort == "oldest":
        query = query.order_by(Ticket.created_at.asc())
    elif sort == "priority":
        query = query.order_by(PRIORITY_SORT, Ticket.created_at.desc())
    elif sort == "updated":
        query = query.order_by(Ticket.updated_at.desc())
    else:
        query = query.order_by(Ticket.created_at.desc())
    tickets = list(session.scalars(query.limit(limit).offset(offset)).unique().all())

    facets = {
        "category": _facet(session, Ticket.category),
        "priority": _facet(session, Ticket.priority),
        "status": _facet(session, Ticket.status),
    }
    return tickets, total, facets


def _facet(session: Session, column) -> dict[str, int]:  # type: ignore[no-untyped-def]
    rows = session.execute(select(column, func.count()).group_by(column)).all()
    return {str(value): int(count) for value, count in rows}


def list_articles(session: Session, *, search: str | None = None, category: str | None = None) -> list[KnowledgeArticle]:
    query = select(KnowledgeArticle)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                KnowledgeArticle.title.ilike(pattern),
                KnowledgeArticle.summary.ilike(pattern),
                KnowledgeArticle.content.ilike(pattern),
            )
        )
    if category:
        query = query.where(KnowledgeArticle.category == category)
    return list(session.scalars(query.order_by(KnowledgeArticle.category, KnowledgeArticle.title)).all())


def ticket_counts(session: Session) -> dict[str, int]:
    total = session.scalar(select(func.count()).select_from(Ticket)) or 0
    articles = session.scalar(select(func.count()).select_from(KnowledgeArticle)) or 0
    status_rows = session.execute(select(Ticket.status, func.count()).group_by(Ticket.status)).all()
    counts = {str(status): int(count) for status, count in status_rows}
    return {
        "tickets": int(total),
        "articles": int(articles),
        "new": counts.get("new", 0),
        "in_progress": counts.get("in_progress", 0),
        "escalated": counts.get("escalated", 0),
        "resolved": counts.get("resolved", 0),
    }


def latest_event_detail(ticket: Ticket) -> str:
    if not ticket.events:
        return ""
    return f"{ticket.events[-1].action} · {iso(ticket.events[-1].created_at)}"