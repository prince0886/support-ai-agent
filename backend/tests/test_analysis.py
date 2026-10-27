"""Deterministic analyst behaviour on the demo corpus."""

from __future__ import annotations

import pytest

from app.analysis import SupportAnalyst
from app.config import Settings
from app.demo_data import DEMO_TICKETS, KNOWLEDGE_ARTICLES
from app.models import KnowledgeArticle

SCENARIOS = {ticket["customer_name"]: ticket for ticket in DEMO_TICKETS}


@pytest.fixture(scope="module")
def articles() -> list[KnowledgeArticle]:
    return [KnowledgeArticle(**item, id=index + 1) for index, item in enumerate(KNOWLEDGE_ARTICLES)]


@pytest.fixture(scope="module")
def analyst() -> SupportAnalyst:
    return SupportAnalyst(Settings(llm_enabled=False))


def analyze(analyst: SupportAnalyst, articles: list[KnowledgeArticle], name: str):
    ticket = SCENARIOS[name]
    return analyst.analyze_deterministic(
        message=ticket["message"],
        customer_name=ticket["customer_name"],
        articles=articles,
    )


def test_delayed_shipment_is_routine_high_priority(analyst, articles):
    result = analyze(analyst, articles, "Maya Chen")
    assert result.category.value == "shipping"
    assert result.priority.value == "high"
    assert result.requires_human is False
    assert result.retrieved[0].article.slug == "shipping-delays"
    assert "carrier" in result.draft_reply.lower()


def test_refund_request_is_grounded_and_routine(analyst, articles):
    result = analyze(analyst, articles, "Daniel Okafor")
    assert result.category.value == "refund"
    assert result.requires_human is False
    assert result.retrieved[0].article.slug == "refund-policy"
    draft = result.draft_reply.lower()
    assert "30 days" in draft or "30-day" in draft
    # A draft must never approve money movement.
    assert "refund has been approved" not in draft
    assert "we have approved" not in draft


def test_failed_payment_escalates(analyst, articles):
    result = analyze(analyst, articles, "Priya Raman")
    assert result.category.value == "billing"
    assert result.requires_human is True
    assert "Financial decision" in result.risk_flags
    assert "never authorizes refunds" in (result.escalation_reason or "").lower()


def test_blocking_technical_issue_escalates(analyst, articles):
    result = analyze(analyst, articles, "Tom Becker")
    assert result.category.value == "technical_support"
    assert result.requires_human is True
    assert result.priority.value == "urgent"
    assert "Blocking outage" in result.risk_flags
    assert result.retrieved[0].article.slug == "app-troubleshooting"


def test_policy_exception_is_flagged_for_a_supervisor(analyst, articles):
    result = analyze(analyst, articles, "Angela Torres")
    assert result.category.value == "refund"
    assert result.requires_human is True
    assert "Policy exception" in result.risk_flags
    assert "supervisor" in (result.escalation_reason or "").lower()
    assert result.retrieved[0].article.slug == "refund-exceptions"
    assert result.sentiment.value == "angry"


def test_missing_parcel_needs_investigation(analyst, articles):
    result = analyze(analyst, articles, "Sam Whitfield")
    assert result.requires_human is True
    assert "Order investigation" in result.risk_flags
    assert result.retrieved[0].article.slug == "lost-or-missing-package"


def test_general_question_is_low_priority(analyst, articles):
    result = analyze(analyst, articles, "Aiko Tanaka")
    assert result.category.value == "shipping"
    assert result.priority.value == "low"
    assert result.requires_human is False
    assert result.retrieved[0].article.slug == "international-shipping"


def test_unmatched_question_never_invents_policy(analyst):
    result = analyst.analyze_deterministic(
        message="Do you offer a lifetime warranty on the Northwind Voyager kayak and a free paddle?",
        customer_name="Jordan",
        articles=[KnowledgeArticle(**KNOWLEDGE_ARTICLES[0], id=1)],
    )
    assert "not have a documented answer" in result.draft_reply.lower()
    assert result.requires_human is True


def test_short_ambiguous_message_is_escalated(analyst, articles):
    result = analyst.analyze_deterministic(
        message="help",
        customer_name="Anonymous",
        articles=articles,
    )
    assert result.requires_human is True
    assert "Unclear request" in result.risk_flags