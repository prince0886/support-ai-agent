"""Ticket endpoints: intake, review queue, AI analysis and human actions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..domain import CATEGORY_LABELS, Category, Priority, TicketStatus
from ..schemas import (
    ApproveRequest,
    DraftUpdate,
    EscalateRequest,
    MessageCreate,
    ReopenRequest,
    ResolveRequest,
    TicketCreate,
    TicketDetail,
    TicketListResponse,
    TicketUpdate,
)
from ..serializers import ticket_detail, ticket_summary
from ..service import (
    InvalidTransition,
    TicketNotFound,
    add_message,
    approve_reply,
    create_ticket,
    escalate_ticket,
    get_ticket,
    list_tickets,
    reanalyze_ticket,
    reopen_ticket,
    resolve_ticket,
    save_draft,
    update_ticket,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _detail(session: Session, ticket_id: int) -> dict:
    try:
        return ticket_detail(get_ticket(session, ticket_id))
    except TicketNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("", response_model=TicketListResponse)
def list_endpoint(
    session: Session = Depends(get_db),
    q: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    requires_human: bool | None = Query(default=None),
    sort: str = Query(default="newest", pattern="^(newest|oldest|priority|updated)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    if category and category not in {item.value for item in Category}:
        raise HTTPException(status_code=422, detail=f"Unknown category '{category}'")
    if priority and priority not in {item.value for item in Priority}:
        raise HTTPException(status_code=422, detail=f"Unknown priority '{priority}'")
    if status_filter and status_filter not in {item.value for item in TicketStatus}:
        raise HTTPException(status_code=422, detail=f"Unknown status '{status_filter}'")

    tickets, total, facets = list_tickets(
        session,
        search=q,
        category=category,
        priority=priority,
        status=status_filter,
        requires_human=requires_human,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [ticket_summary(ticket) for ticket in tickets],
        "total": total,
        "facets": facets,
    }


@router.post("", response_model=TicketDetail, status_code=status.HTTP_201_CREATED)
async def create_endpoint(payload: TicketCreate, request: Request, session: Session = Depends(get_db)) -> dict:
    analyst = request.app.state.analyst
    ticket = await create_ticket(session, analyst, payload, use_llm=True)
    return _detail(session, ticket.id)


@router.get("/{ticket_id}", response_model=TicketDetail)
def get_endpoint(ticket_id: int, session: Session = Depends(get_db)) -> dict:
    return _detail(session, ticket_id)


@router.patch("/{ticket_id}", response_model=TicketDetail)
def update_endpoint(ticket_id: int, payload: TicketUpdate, session: Session = Depends(get_db)) -> dict:
    ticket = get_ticket(session, ticket_id)
    try:
        update_ticket(session, ticket, payload)
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _detail(session, ticket_id)


@router.post("/{ticket_id}/reanalyze", response_model=TicketDetail)
async def reanalyze_endpoint(ticket_id: int, request: Request, session: Session = Depends(get_db)) -> dict:
    ticket = get_ticket(session, ticket_id)
    await reanalyze_ticket(session, request.app.state.analyst, ticket, use_llm=True)
    return _detail(session, ticket_id)


@router.post("/{ticket_id}/draft", response_model=TicketDetail)
def save_draft_endpoint(ticket_id: int, payload: DraftUpdate, session: Session = Depends(get_db)) -> dict:
    ticket = get_ticket(session, ticket_id)
    try:
        save_draft(session, ticket, payload.body)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _detail(session, ticket_id)


@router.post("/{ticket_id}/approve", response_model=TicketDetail)
def approve_endpoint(ticket_id: int, payload: ApproveRequest, session: Session = Depends(get_db)) -> dict:
    ticket = get_ticket(session, ticket_id)
    try:
        approve_reply(session, ticket, payload.body, payload.note)
    except ValueError as exc:
        # Resolved tickets and empty drafts are state conflicts, not bad input.
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _detail(session, ticket_id)


@router.post("/{ticket_id}/resolve", response_model=TicketDetail)
def resolve_endpoint(ticket_id: int, payload: ResolveRequest, session: Session = Depends(get_db)) -> dict:
    ticket = get_ticket(session, ticket_id)
    resolve_ticket(session, ticket, payload.body, payload.note)
    return _detail(session, ticket_id)


@router.post("/{ticket_id}/escalate", response_model=TicketDetail)
def escalate_endpoint(ticket_id: int, payload: EscalateRequest, session: Session = Depends(get_db)) -> dict:
    ticket = get_ticket(session, ticket_id)
    escalate_ticket(session, ticket, payload.reason)
    return _detail(session, ticket_id)


@router.post("/{ticket_id}/reopen", response_model=TicketDetail)
def reopen_endpoint(ticket_id: int, payload: ReopenRequest, session: Session = Depends(get_db)) -> dict:
    ticket = get_ticket(session, ticket_id)
    reopen_ticket(session, ticket, payload.note)
    return _detail(session, ticket_id)


@router.post("/{ticket_id}/messages", response_model=TicketDetail)
def message_endpoint(ticket_id: int, payload: MessageCreate, session: Session = Depends(get_db)) -> dict:
    ticket = get_ticket(session, ticket_id)
    add_message(session, ticket, payload.body, internal=payload.internal)
    return _detail(session, ticket_id)


@router.get("/meta/categories")
def categories_endpoint() -> dict:
    return {"items": [{"value": item.value, "label": CATEGORY_LABELS[item]} for item in Category]}