"""Shared domain vocabulary used by the API, the analysis engine and the UI."""

from __future__ import annotations

from enum import Enum


class Category(str, Enum):
    BILLING = "billing"
    REFUND = "refund"
    SHIPPING = "shipping"
    TECHNICAL = "technical_support"
    GENERAL = "general_inquiry"

    @property
    def label(self) -> str:
        return CATEGORY_LABELS[self]


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketStatus(str, Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    ESCALATED = "escalated"
    RESOLVED = "resolved"


class DraftStatus(str, Enum):
    DRAFT = "draft"
    EDITED = "edited"
    APPROVED = "approved"


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    FRUSTRATED = "frustrated"
    ANGRY = "angry"


class MessageRole(str, Enum):
    CUSTOMER = "customer"
    ASSISTANT = "assistant"  # approved / sent agent reply
    NOTE = "note"  # internal note
    SYSTEM = "system"


CATEGORY_LABELS: dict[Category, str] = {
    Category.BILLING: "Billing",
    Category.REFUND: "Refund",
    Category.SHIPPING: "Shipping",
    Category.TECHNICAL: "Technical Support",
    Category.GENERAL: "General Inquiry",
}

CATEGORIES: list[Category] = list(Category)
PRIORITIES: list[Priority] = list(Priority)
STATUSES: list[TicketStatus] = list(TicketStatus)

OPEN_STATUSES = (TicketStatus.NEW, TicketStatus.IN_PROGRESS, TicketStatus.ESCALATED)

# Statuses an agent can move a ticket to from any other state.
ALLOWED_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.NEW: {TicketStatus.NEW, TicketStatus.IN_PROGRESS, TicketStatus.ESCALATED, TicketStatus.RESOLVED},
    TicketStatus.IN_PROGRESS: {
        TicketStatus.NEW,
        TicketStatus.IN_PROGRESS,
        TicketStatus.ESCALATED,
        TicketStatus.RESOLVED,
    },
    TicketStatus.ESCALATED: {TicketStatus.ESCALATED, TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED},
    TicketStatus.RESOLVED: {TicketStatus.RESOLVED, TicketStatus.IN_PROGRESS, TicketStatus.ESCALATED},
}