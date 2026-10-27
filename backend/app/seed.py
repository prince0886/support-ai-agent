"""Seed the demo knowledge base and the scripted demo tickets."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from .analysis import SupportAnalyst
from .config import Settings
from .database import Base
from .demo_data import DEMO_TICKETS, KNOWLEDGE_ARTICLES
from .llm import LLMClient
from .models import KnowledgeArticle, Ticket, TicketEvent, TicketMessage
from .schemas import TicketCreate
from .service import create_ticket, get_ticket
from .utils import utcnow

logger = logging.getLogger(__name__)


async def seed_database(
    session_factory: sessionmaker[Session],
    settings: Settings,
    *,
    force: bool = False,
) -> dict:
    with session_factory() as session:
        article_count = session.scalar(select(func.count()).select_from(KnowledgeArticle)) or 0
        ticket_count = session.scalar(select(func.count()).select_from(Ticket)) or 0

        # Fully seeded: nothing to do. A partially seeded database (articles but
        # no tickets, or the reverse) is repaired below by filling only the part
        # that is missing, so a run is never duplicated.
        if not force and article_count and ticket_count:
            return {"seeded": False, "tickets": int(ticket_count), "articles": int(article_count)}

        if force and (article_count or ticket_count):
            session.query(TicketMessage).delete()
            session.query(TicketEvent).delete()
            session.query(Ticket).delete()
            session.query(KnowledgeArticle).delete()
            session.commit()
            article_count = 0
            ticket_count = 0

        if article_count:
            logger.info("Knowledge base already holds %s articles; skipping article seed", article_count)
        else:
            session.add_all([KnowledgeArticle(**article) for article in KNOWLEDGE_ARTICLES])
            session.commit()
            article_count = len(KNOWLEDGE_ARTICLES)

        if ticket_count:
            logger.info("Inbox already holds %s tickets; skipping demo ticket seed", ticket_count)
            return {"seeded": False, "tickets": int(ticket_count), "articles": article_count}

        analyst = SupportAnalyst(settings, LLMClient(settings))
        now = utcnow()
        seeded = 0

        # Oldest first so reference numbers line up with creation time.
        for demo in sorted(DEMO_TICKETS, key=lambda item: item["hours_ago"], reverse=True):
            created_at = now - timedelta(hours=demo["hours_ago"])
            payload = TicketCreate(
                message=demo["message"],
                customer_name=demo["customer_name"],
                customer_email=demo["customer_email"],
                subject=demo["subject"],
                channel=demo.get("channel", "email"),
            )
            ticket = await create_ticket(session, analyst, payload, use_llm=False, created_at=created_at)
            await _apply_demo_history(session, ticket, demo, created_at)
            seeded += 1

        logger.info("Seeded %s demo tickets and %s knowledge articles", seeded, len(KNOWLEDGE_ARTICLES))
        return {"seeded": True, "tickets": seeded, "articles": len(KNOWLEDGE_ARTICLES)}


async def _apply_demo_history(session: Session, ticket: Ticket, demo: dict, created_at: datetime) -> None:
    status = demo["status"]
    conversation = demo.get("conversation", [])
    last_reply_at = created_at

    for entry in conversation:
        sent_at = created_at + timedelta(hours=entry["hours_after"])
        last_reply_at = max(last_reply_at, sent_at)
        role = entry["role"]
        ticket.messages.append(
            TicketMessage(
                role=role,
                author=entry.get("author", "Agent Rhea"),
                body=entry["body"],
                is_internal=role == "note",
                created_at=sent_at,
            )
        )
        if role == "assistant":
            ticket.approved_reply = entry["body"]
            ticket.approved_at = sent_at
            ticket.draft_reply = entry["body"]
            ticket.draft_status = "approved"

    if status == "escalated":
        ticket.status = "escalated"
        ticket.requires_human = True
        ticket.escalation_reason = demo.get("escalation_reason") or ticket.escalation_reason
        ticket.updated_at = created_at + timedelta(hours=2)
        ticket.events.append(
            TicketEvent(
                action="escalated",
                detail=f"Escalated to a supervisor: {ticket.escalation_reason}",
                actor="Human agent",
                created_at=created_at + timedelta(hours=2),
            )
        )
    elif status == "resolved":
        ticket.status = "resolved"
        ticket.resolved_at = last_reply_at + timedelta(minutes=40)
        ticket.updated_at = ticket.resolved_at
        ticket.events.append(
            TicketEvent(
                action="resolved",
                detail="Ticket marked resolved by a human agent.",
                actor="Human agent",
                created_at=ticket.resolved_at,
            )
        )
    elif status == "in_progress":
        ticket.status = "in_progress"
        ticket.updated_at = last_reply_at
        ticket.events.append(
            TicketEvent(
                action="approved",
                detail="Human agent approved a reply and moved the ticket to in progress.",
                actor="Human agent",
                created_at=last_reply_at,
            )
        )

    session.commit()
    get_ticket(session, ticket.id)


async def reset_database(engine: Engine, session_factory: sessionmaker[Session], settings: Settings) -> dict:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return await seed_database(session_factory, settings, force=True)