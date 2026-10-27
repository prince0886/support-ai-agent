"""LLM integration: structured output, guardrails and provider failure fallback.

The provider is simulated with httpx.MockTransport, so these tests prove the real
request/response handling without needing a live API key.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.analysis import SupportAnalyst
from app.config import Settings
from app.demo_data import KNOWLEDGE_ARTICLES, DEMO_TICKETS
from app.llm import LLMClient, extract_json_object
from app.models import KnowledgeArticle

ARTICLES = [KnowledgeArticle(**item, id=index + 1) for index, item in enumerate(KNOWLEDGE_ARTICLES)]
SCENARIOS = {ticket["customer_name"]: ticket for ticket in DEMO_TICKETS}

GOOD_DRAFT = (
    "Hi Maya,\n\nThanks for reaching out. Carrier delays of 1 to 3 business days are common, and the parcel "
    "usually keeps moving. If tracking has not updated for more than 5 business days past the estimated "
    "delivery date, we can open a carrier investigation.\n\nBest regards,\nNorthwind Support Team"
)


def llm_settings() -> Settings:
    return Settings(
        llm_enabled=True,
        llm_api_key="test-key",
        llm_base_url="https://llm.test/v1",
        llm_model="mock-model",
        llm_timeout_seconds=5,
    )


def payload(**overrides) -> dict:
    base = {
        "category": "shipping",
        "priority": "medium",
        "intent": "Delayed shipment",
        "sentiment": "frustrated",
        "classification_reason": "The customer says tracking has not moved in six days.",
        "confidence": 0.88,
        "requires_human": False,
        "escalation_reason": None,
        "risk_flags": [],
        "draft_reply": GOOD_DRAFT,
    }
    base.update(overrides)
    return base


def build_analyst(body: dict | str | None, *, status_code: int = 200, captured: list | None = None) -> SupportAnalyst:
    def handler(request: httpx.Request) -> httpx.Response:
        if captured is not None:
            captured.append(json.loads(request.content))
        if status_code != 200:
            return httpx.Response(status_code, json={"error": {"message": "provider down"}})
        content = body if isinstance(body, str) else json.dumps(body)
        return httpx.Response(
            200,
            json={"model": "mock-model", "choices": [{"message": {"content": content}}]},
        )

    settings = llm_settings()
    llm = LLMClient(settings, transport=httpx.MockTransport(handler))
    return SupportAnalyst(settings, llm)


async def analyze(analyst: SupportAnalyst, customer: str = "Maya Chen"):
    scenario = SCENARIOS[customer]
    return await analyst.analyze(
        message=scenario["message"],
        customer_name=scenario["customer_name"],
        articles=ARTICLES,
    )


async def test_llm_output_is_used_and_prompt_is_grounded():
    captured: list[dict] = []
    analyst = build_analyst(payload(), captured=captured)
    result = await analyze(analyst)

    assert result.ai_mode == "llm"
    assert result.ai_model == "mock-model"
    assert result.category.value == "shipping"
    assert result.draft_reply == GOOD_DRAFT
    assert result.sentiment.value == "frustrated"
    assert result.classification_reason.startswith("The customer says tracking")

    request = captured[0]
    prompt = request["messages"][1]["content"]
    assert "What to do when a shipment is delayed" in prompt
    assert "Maya Chen" in prompt
    assert request["response_format"] == {"type": "json_object"}


async def test_llm_cannot_downgrade_deterministic_urgency():
    analyst = build_analyst(payload(priority="low"))
    result = await analyze(analyst)
    assert result.priority.value == "high"  # deterministic urgency wins
    assert any("Priority raised" in note for note in result.guardrail_notes)


async def test_llm_cannot_skip_a_required_escalation():
    analyst = build_analyst(payload(category="refund", requires_human=False, draft_reply="ok"))
    result = await analyze(analyst, customer="Angela Torres")
    assert result.requires_human is True
    assert result.escalation_reason
    assert "Policy exception" in result.risk_flags


async def test_commitment_in_llm_draft_is_discarded():
    analyst = build_analyst(
        payload(
            category="refund",
            requires_human=False,
            draft_reply="Hi Angela,\n\nWe have approved your refund of $340 and it will arrive by Friday.\n\nBest regards,\nNorthwind Support Team",
        )
    )
    result = await analyze(analyst, customer="Angela Torres")
    assert result.requires_human is True
    assert "Draft guardrail" in result.risk_flags
    assert "we have approved your refund" not in result.draft_reply.lower()
    assert any("commitment" in note.lower() for note in result.guardrail_notes)
    # Falls back to the grounded deterministic draft.
    assert "exceptions" in result.draft_reply.lower() or "supervisor" in result.draft_reply.lower()


async def test_no_knowledge_coverage_forces_human_review_even_with_llm():
    analyst = SupportAnalyst(
        llm_settings(),
        LLMClient(
            llm_settings(),
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={
                        "model": "mock-model",
                        "choices": [
                            {
                                "message": {
                                    "content": json.dumps(
                                        payload(
                                            category="general_inquiry",
                                            priority="low",
                                            draft_reply="Hello,\n\nYes, the kayak comes with a lifetime warranty.\n\nBest regards,\nNorthwind Support Team",
                                        )
                                    )
                                }
                            }
                        ],
                    },
                )
            ),
        ),
    )
    result = await analyst.analyze(
        message="Do you offer a lifetime warranty on the Northwind Voyager kayak and a free paddle?",
        customer_name="Jordan",
        articles=[ARTICLES[0]],
    )
    assert result.requires_human is True
    assert "knowledge base" in (result.escalation_reason or "").lower()


async def test_provider_error_falls_back_to_deterministic_analyst():
    analyst = build_analyst(None, status_code=503)
    result = await analyze(analyst)
    assert result.ai_mode == "fallback"
    assert result.ai_model == "deterministic-analyst-v1"
    assert result.draft_reply
    assert "503" in (analyst.llm.last_error or "")


async def test_invalid_json_falls_back():
    analyst = build_analyst("I cannot answer that in JSON.")
    result = await analyze(analyst)
    assert result.ai_mode == "fallback"
    assert "JSON" in (analyst.llm.last_error or "").upper() or analyst.llm.last_error


async def test_incomplete_json_falls_back():
    analyst = build_analyst({"category": "", "priority": "medium", "draft_reply": "hi"})
    result = await analyze(analyst)
    assert result.ai_mode == "fallback"


def test_extract_json_object_handles_code_fences():
    parsed = extract_json_object('```json\n{"category": "billing", "confidence": 0.7}\n```')
    assert parsed["category"] == "billing"

    with pytest.raises(ValueError):
        extract_json_object("no json here")