"""Ticket analysis: classify, prioritise, retrieve, draft and decide on escalation.

Two interchangeable engines produce the *same* result shape:

1. The configured LLM (any OpenAI-compatible endpoint) does classification and
   drafting in one JSON call.
2. The built-in deterministic analyst scores category keywords, applies explicit
   escalation rules and composes a reply from retrieved knowledge-base excerpts.

The LLM path is always bounded by deterministic guardrails: a human-review rule
that the model missed is still enforced, a draft that promises money movement is
discarded, and provider failures degrade silently to the deterministic analyst.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from pydantic import BaseModel, Field, field_validator

from .config import Settings
from .domain import Category, Priority, Sentiment
from .knowledge import KnowledgeIndex, RetrievedArticle
from .llm import LLMClient
from .models import KnowledgeArticle
from .utils import first_name

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Heuristic vocabulary
# ---------------------------------------------------------------------------

CATEGORY_TERMS: dict[Category, dict[str, int]] = {
    Category.BILLING: {
        "payment": 2, "paid": 1, "pay": 1, "charge": 3, "charged": 3, "invoice": 3, "billing": 3,
        "card": 2, "declined": 3, "decline": 3, "transaction": 2, "subscription": 2, "renew": 2,
        "renewal": 2, "receipt": 2, "price": 1, "overcharged": 3, "double charged": 3, "duplicate": 2,
        "statement": 1, "bank": 1, "checkout": 1, "payment method": 2, "pending charge": 3,
    },
    Category.REFUND: {
        "refund": 4, "refunded": 4, "money back": 4, "return": 3, "returned": 3, "reimburse": 4,
        "reimbursement": 4, "exchange": 2, "warranty": 2, "rma": 3, "store credit": 2,
        "send it back": 3, "send back": 3, "unwanted": 1, "return label": 3,
    },
    Category.SHIPPING: {
        "shipping": 3, "shipment": 3, "shipped": 2, "delivery": 3, "delivered": 3, "deliver": 2,
        "package": 2, "parcel": 3, "courier": 3, "tracking": 3, "dispatch": 2, "carrier": 1,
        "arrive": 2, "arrived": 2, "late": 2, "delayed": 3, "delay": 3, "order status": 2,
        "where is my order": 4, "address": 1, "warehouse": 1, "label created": 3,
    },
    Category.TECHNICAL: {
        "error": 3, "bug": 3, "crash": 3, "crashing": 3, "not working": 3, "broken": 2,
        "login": 3, "log in": 3, "sign in": 3, "signin": 3, "password": 2, "reset": 1, "locked": 1,
        "locked out": 2, "app": 1, "website": 1, "dashboard": 2, "install": 2, "update": 1,
        "sync": 2, "glitch": 2, "freeze": 2, "500": 3, "timeout": 2, "upload": 2, "2fa": 3,
        "two-factor": 3, "two factor": 3, "verification code": 2, "browser": 1, "page": 1,
        "loading": 1, "spinning": 2,
    },
    Category.GENERAL: {
        "hours": 2, "contact": 1, "question": 1, "how do i": 1, "account": 1, "feedback": 1,
        "ship to": 1, "international": 1, "profile": 2, "email": 2, "change my": 2,
    },
}

PRIORITY_BASE: dict[Category, int] = {
    Category.BILLING: 2,
    Category.REFUND: 2,
    Category.SHIPPING: 2,
    Category.TECHNICAL: 3,
    Category.GENERAL: 1,
}

PRIORITY_SIGNALS: list[tuple[str, int]] = [
    ("urgent", 3), ("asap", 2), ("immediately", 2), ("right now", 2), ("today", 1),
    ("completely blocked", 4), ("blocked", 2), ("cannot access", 3), ("cant access", 3),
    ("locked out", 2), ("data loss", 4), ("outage", 3), ("production", 2), ("down", 1),
    ("unauthorized", 3), ("fraud", 3), ("stolen", 2), ("hacked", 3),
    ("chargeback", 3), ("disputing the charge", 3), ("dispute", 2), ("legal", 3), ("lawyer", 3),
    ("sue", 3), ("charged twice", 3), ("double charged", 3), ("duplicate charge", 3),
    ("declined", 2), ("pending", 1), ("missing", 2), ("lost", 2), ("delivered but", 2),
    ("nothing arrived", 2), ("never arrived", 2), ("never received", 2), ("missing", 2),
    ("damaged", 2), ("wrong item", 2), ("third time", 2), ("again", 1), ("still", 1),
    ("repeatedly", 1), ("deadline", 2), ("trip", 1), ("birthday", 1), ("delayed", 1),
    ("late", 1), ("stuck", 1), ("label created", 1), ("not updated", 2), ("no update", 2),
    ("been waiting", 1), ("never showed", 2), ("supposed to arrive", 1), ("days ago", 1),
]

ANGRY_WORDS = (
    "furious", "ridiculous", "unacceptable", "outrageous", "terrible", "worst", "angry",
    "fed up", "sick of", "scam", "disgusted", "never again", "appalling", "disgraceful",
    "frustrating", "insane", "pathetic",
)
FRUSTRATED_WORDS = (
    "disappointed", "frustrated", "annoyed", "still waiting", "third time", "not happy",
    "poor", "unresolved", "no response", "let down", "again",
)
POSITIVE_WORDS = ("thanks", "thank you", "appreciate", "great", "perfect", "love it")

INTENT_RULES: dict[Category, list[tuple[str, str]]] = {
    Category.SHIPPING: [
        (r"\b(missing|lost|marked delivered|never arrived|nothing arrived|delivered but)\b", "Missing package claim"),
        (r"\b(damaged|broken|wrong item|incorrect item)\b", "Damaged or incorrect item"),
        (r"\b(address|change the address|ship to a different)\b", "Address change request"),
        (r"\b(international|ship to|japan|canada|europe|australia|duties|customs|outside the us)\b", "International shipping question"),
        (r"\b(delay|delayed|late|stuck|label created|tracking|where is my order)\b", "Shipment delay / tracking question"),
    ],
    Category.REFUND: [
        (r"\b(exception|waive|goodwill|past|outside).{0,30}\b(window|policy|days?)\b", "Policy exception request"),
        (r"\b(where.{0,10}(is|s) my refund|refund.{0,30}(status|still|waiting|not (arrived|received)))\b", "Refund status inquiry"),
        (r"\b(warranty|defective|faulty|manufactur)\b", "Warranty claim"),
        (r"\b(return|send.{0,10}back|exchange)\b", "Return request"),
    ],
    Category.BILLING: [
        (r"\b(duplicate|double|charged twice|two charges)\b", "Duplicate charge"),
        (r"\b(declined|failed|fail|unable to pay|payment did not)\b", "Failed payment"),
        (r"\b(invoice|receipt|pdf)\b", "Invoice request"),
        (r"\b(subscription|renew|plan|cancel)\b", "Subscription billing"),
    ],
    Category.TECHNICAL: [
        (r"\b(2fa|two.factor|authenticator|verification code|backup code)\b", "Two-factor authentication"),
        (r"\b(login|log in|sign in|password|signin|locked out)\b", "Sign-in issue"),
        (r"\b(500|error|crash|spin|loading|dashboard|freeze|glitch)\b", "Application error"),
        (r"\b(update|install|sync|download)\b", "App troubleshooting"),
    ],
    Category.GENERAL: [
        (r"\b(hours|open|response time)\b", "Support hours"),
        (r"\b(email|profile|account details|change my)\b", "Account details"),
        (r"\b(ship to|international|deliver to|japan|europe|canada)\b", "International shipping question"),
    ],
}

TOPIC_PHRASES: dict[Category, str] = {
    Category.SHIPPING: "your delivery",
    Category.REFUND: "your refund request",
    Category.BILLING: "the payment issue",
    Category.TECHNICAL: "the technical problem",
    Category.GENERAL: "your question",
}

ACK_LINES: dict[Category, str] = {
    Category.SHIPPING: "Let me help you with the delivery.",
    Category.REFUND: "I can walk you through the return and refund process.",
    Category.BILLING: "I can help you understand what happened with the payment.",
    Category.TECHNICAL: "Let me help you get this working again.",
    Category.GENERAL: "Happy to help with your question.",
}

NEXT_STEPS: dict[Category, str] = {
    Category.SHIPPING: (
        "If tracking has not moved within 5 business days of the estimated delivery date, reply here "
        "and we can open a carrier investigation, which usually takes 2 to 5 business days."
    ),
    Category.REFUND: (
        "To get started, open Account, then Orders, and choose 'Return or exchange'. The prepaid label "
        "is emailed within a few minutes, and refunds are issued after the item passes inspection."
    ),
    Category.BILLING: (
        "If a pending amount has not cleared after 5 business days, reply with the charge date and the "
        "last four digits of the card and we will review it with the billing team."
    ),
    Category.TECHNICAL: (
        "If that does not help, send the exact error code, your browser or app version and a screenshot "
        "so we can take a closer look."
    ),
    Category.GENERAL: "If you would like more detail, just reply and I will point you to the right place.",
}

INTENT_NEXT_STEPS: dict[str, str] = {
    "Shipment delay / tracking question": (
        "Keep an eye on the tracking link over the next day or two, and reply here with the order number if "
        "it has not moved by then."
    ),
    "Invoice request": (
        "If the month you need is not listed, reply with the invoice date and the email address on the "
        "account and we will send a copy."
    ),
    "Account details": (
        "If the confirmation email does not arrive, tell us and we will check the change from our side."
    ),
    "Support hours": (
        "If your issue is urgent outside those hours, reply here and we will pick it up first thing on the "
        "next business day."
    ),
    "International shipping question": (
        "If your destination is not listed at checkout, reply with the country and we will confirm before "
        "you order."
    ),
    "Refund status inquiry": (
        "Send the order number and the email address used at checkout and we can look up the refund for you."
    ),
    "Return request": (
        "You can start the return under Account, then Orders, and choose 'Return or exchange'. The prepaid "
        "label is emailed within a few minutes."
    ),
    "Subscription billing": (
        "Your renewal date and amount are shown under Account, then Billing, and any change must be made "
        "before the next renewal date."
    ),
    "Sign-in issue": (
        "If the reset link does not arrive within 10 minutes, check the spam folder and confirm the address "
        "matches the account, then request a new link."
    ),
    "Two-factor authentication": (
        "If you still have your backup codes, each one can be used once to sign in. Without them, we start "
        "an identity verification flow before any reset."
    ),
}

INTENT_ACKS: dict[str, str] = {
    "Invoice request": "Happy to help with the invoice.",
    "Account details": "Happy to help with your account details.",
    "Support hours": "Happy to help with that.",
    "International shipping question": "Happy to help with international delivery.",
    "Refund status inquiry": "I can help you look into that refund.",
    "Return request": "I can walk you through the return process.",
    "Shipment delay / tracking question": "Let me help you with the delivery.",
}

# Deterministic topic priors for retrieval. BM25 still drives ranking, but the
# article that owns an intent should not lose to a generic word match.
INTENT_ARTICLE_HINTS: dict[str, tuple[str, ...]] = {
    "Shipment delay / tracking question": ("shipping-delays",),
    "Missing package claim": ("lost-or-missing-package",),
    "Damaged or incorrect item": ("damaged-or-wrong-item",),
    "Address change request": ("shipping-address-changes",),
    "Shipping question": ("shipping-times-and-tracking",),
    "Return request": ("refund-policy", "how-to-start-a-return"),
    "Refund request": ("refund-policy",),
    "Refund status inquiry": ("refund-timeline",),
    "Policy exception request": ("refund-exceptions", "refund-policy"),
    "Warranty claim": ("warranty-and-replacements",),
    "Duplicate charge": ("duplicate-charges", "failed-payments"),
    "Failed payment": ("failed-payments", "duplicate-charges"),
    "Invoice request": ("subscription-billing",),
    "Subscription billing": ("subscription-billing",),
    "Application error": ("app-troubleshooting",),
    "App troubleshooting": ("app-troubleshooting",),
    "Sign-in issue": ("sign-in-help",),
    "Two-factor authentication": ("two-factor-authentication",),
    "Account details": ("account-details",),
    "Support hours": ("support-hours",),
    "International shipping question": ("international-shipping",),
}


# ---------------------------------------------------------------------------
# Escalation rules
# ---------------------------------------------------------------------------


@dataclass
class RiskFlag:
    key: str
    label: str
    reason: str
    short_reason: str


@dataclass
class RiskRule:
    key: str
    label: str
    pattern: re.Pattern[str]
    reason: str
    short_reason: str


RISK_RULES: list[RiskRule] = [
    RiskRule(
        key="policy_exception",
        label="Policy exception",
        pattern=re.compile(
            r"\b(exception|exceptions|waive|waived|waiver|goodwill|bend the rules|special case)\b"
            r"|\b(past|outside|beyond)\b.{0,30}\b(window|policy|deadline|\d+[- ]day)\b"
        ),
        reason=(
            "Policy exception requested: the customer is asking for a decision outside published policy. "
            "Only a human supervisor can approve an exception, and no outcome should be promised first."
        ),
        short_reason="a policy exception that only a supervisor can approve",
    ),
    RiskRule(
        key="financial_decision",
        label="Financial decision",
        pattern=re.compile(
            r"\b(chargeback|charge back|dispute|disputing|compensat\w*|reimburse\w*|double[- ]charg\w*|"
            r"charged twice|duplicate charge|unauthori[sz]ed (charge|payment)|approve (the|my) refund)\b"
            r"|\bwhere.{0,15}(is|s) my refund\b"
            r"|\b(refund|money back).{0,30}(immediately|asap|today|status|still|waiting|not (received|arrived))\b"
        ),
        reason=(
            "Financial decision: the message involves money movement, a possible duplicate charge or a "
            "refund approval. SupportPilot never authorizes refunds or reversals on its own."
        ),
        short_reason="a payment decision that needs a human to sign off",
    ),
    RiskRule(
        key="sensitive_complaint",
        label="Sensitive complaint",
        pattern=re.compile(
            r"\b(lawyer|attorney|legal action|lawsuit|sue|suing|court|ombudsman|better business bureau|bbb|"
            r"ftc|regulator|social media|trustpilot|review|going public|posting|never (shopping|buying) again|"
            r"unacceptable|ridiculous|furious|disgusted|scam)\b"
        ),
        reason=(
            "Sensitive complaint: the message carries strong dissatisfaction or a public or legal escalation "
            "threat, so a human agent should own the response."
        ),
        short_reason="the sensitivity of the complaint",
    ),
    RiskRule(
        key="security_review",
        label="Security check",
        pattern=re.compile(
            r"\b(hacked|hacker|unauthori[sz]ed access|account (was )?(compromised|hacked)|someone (logged|signed) in|"
            r"identity theft|stolen account|fraud)\b"
        ),
        reason=(
            "Security check: account access or unauthorized activity must be verified by a human before any "
            "account change."
        ),
        short_reason="an account security check",
    ),
    RiskRule(
        key="order_investigation",
        label="Order investigation",
        pattern=re.compile(
            r"\b(missing|lost|never (arrived|received)|marked (as )?delivered|delivered but|nothing arrived|"
            r"stolen|damaged|broken on arrival|wrong item|incorrect item)\b"
        ),
        reason=(
            "Parcel investigation needed: a missing, damaged or misdelivered order has to be verified with the "
            "carrier before a replacement or refund can be discussed."
        ),
        short_reason="an order investigation with the carrier",
    ),
    RiskRule(
        key="blocking_outage",
        label="Blocking outage",
        pattern=re.compile(
            r"\b(completely blocked|totally blocked|entire team|whole team|all (users|accounts)|"
            r"production (is )?down|outage|data loss|cannot work|cant work|cant access anything)\b"
        ),
        reason=(
            "Blocking outage: a whole team is affected, so engineering must confirm the root cause and the "
            "timeline before a resolution is communicated."
        ),
        short_reason="an outage that affects a whole team",
    ),
]

COMMITMENT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\byour refund (has been|is|was) approved\b"),
    re.compile(r"\b(we|i) (have|'ve) (approved|issued|processed) (a |the |your )?refund\b"),
    re.compile(r"\byour (order|parcel|package) (has been|is) (shipped|dispatched|out for delivery)\b"),
    re.compile(r"\b(will|should) (arrive|be delivered|be with you) (by|on) (monday|tuesday|wednesday|thursday|friday|saturday|sunday|\d)"),
    re.compile(r"\bwe (guarantee|promise)\b"),
    re.compile(r"\bcompensation of \$"),
    re.compile(r"\b(we|i) (have|'ve) (cancelled|canceled) your (order|subscription)\b"),
    re.compile(r"\[[^\]]{2,40}\]"),
]

CATEGORY_ALIASES: dict[str, Category] = {
    "billing": Category.BILLING,
    "payment": Category.BILLING,
    "payments": Category.BILLING,
    "refund": Category.REFUND,
    "refunds": Category.REFUND,
    "returns": Category.REFUND,
    "shipping": Category.SHIPPING,
    "delivery": Category.SHIPPING,
    "logistics": Category.SHIPPING,
    "technical": Category.TECHNICAL,
    "technical_support": Category.TECHNICAL,
    "technical support": Category.TECHNICAL,
    "tech": Category.TECHNICAL,
    "general": Category.GENERAL,
    "general_inquiry": Category.GENERAL,
    "general inquiry": Category.GENERAL,
    "other": Category.GENERAL,
}

PRIORITY_ORDER = [Priority.LOW, Priority.MEDIUM, Priority.HIGH, Priority.URGENT]


# ---------------------------------------------------------------------------
# Result shapes
# ---------------------------------------------------------------------------


@dataclass
class HeuristicAnalysis:
    category: Category
    priority: Priority
    intent: str
    sentiment: Sentiment
    classification_reason: str
    confidence: float
    flags: list[RiskFlag]
    draft_reply: str
    category_scores: dict[Category, int]
    matched_terms: list[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    category: Category
    priority: Priority
    intent: str
    sentiment: Sentiment
    classification_reason: str
    confidence: float
    requires_human: bool
    escalation_reason: str | None
    risk_flags: list[str]
    suggested_action: str
    draft_reply: str
    retrieved: list[RetrievedArticle]
    ai_mode: str
    ai_provider: str
    ai_model: str
    guardrail_notes: list[str] = field(default_factory=list)


class LLMAnalysis(BaseModel):
    category: str = ""
    priority: str = ""
    intent: str = ""
    sentiment: str = "neutral"
    classification_reason: str = ""
    confidence: float = 0.65
    requires_human: bool = False
    escalation_reason: str | None = None
    risk_flags: list[str] = Field(default_factory=list)
    draft_reply: str = ""

    @field_validator("category", mode="before")
    @classmethod
    def _category(cls, value: object) -> str:
        if not isinstance(value, str):
            return ""
        normalized = value.strip().lower().replace("-", "_")
        category = CATEGORY_ALIASES.get(normalized) or CATEGORY_ALIASES.get(normalized.replace("_", " "))
        return category.value if category else ""

    @field_validator("priority", mode="before")
    @classmethod
    def _priority(cls, value: object) -> str:
        if not isinstance(value, str):
            return ""
        normalized = value.strip().lower()
        return normalized if normalized in {p.value for p in Priority} else ""

    @field_validator("sentiment", mode="before")
    @classmethod
    def _sentiment(cls, value: object) -> str:
        if not isinstance(value, str):
            return "neutral"
        normalized = value.strip().lower()
        return normalized if normalized in {s.value for s in Sentiment} else "neutral"

    @field_validator("confidence")
    @classmethod
    def _confidence(cls, value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @field_validator("risk_flags", mode="before")
    @classmethod
    def _flags(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value.strip()] if value.strip() else []
        if isinstance(value, list):
            return [str(item).strip()[:60] for item in value if str(item).strip()]
        return []

    @field_validator("draft_reply", "classification_reason", "intent", mode="before")
    @classmethod
    def _text(cls, value: object) -> str:
        return value.strip() if isinstance(value, str) else ""

    @field_validator("escalation_reason", mode="before")
    @classmethod
    def _optional_text(cls, value: object) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class SupportAnalyst:
    def __init__(self, settings: Settings, llm: LLMClient | None = None) -> None:
        self.settings = settings
        self.llm = llm or LLMClient(settings)

    # -- public API ---------------------------------------------------------

    def retrieve(
        self,
        message: str,
        articles: list[KnowledgeArticle],
        *,
        preferred_category: str | None = None,
        hint_slugs: tuple[str, ...] = (),
    ) -> list[RetrievedArticle]:
        index = KnowledgeIndex(articles)
        return index.search(
            message,
            top_k=max(1, self.settings.retrieval_top_k),
            preferred_category=preferred_category,
            hint_slugs=hint_slugs,
        )

    def priors(self, message: str) -> tuple[Category, str]:
        """Cheap keyword category/intent used to bias retrieval before scoring."""
        text = _normalize(message)
        category, _, _ = _classify(text, [])
        return category, _detect_intent(text, category)

    async def analyze(
        self,
        *,
        message: str,
        customer_name: str | None,
        articles: list[KnowledgeArticle],
    ) -> AnalysisResult:
        prior_category, prior_intent = self.priors(message)
        hits = self.retrieve(
            message,
            articles,
            preferred_category=prior_category.value,
            hint_slugs=INTENT_ARTICLE_HINTS.get(prior_intent, ()),
        )
        heuristic = self._heuristic(message, customer_name, hits)

        llm_payload: LLMAnalysis | None = None
        llm_model = ""
        if self.llm.enabled:
            result = await self._call_llm(message, customer_name, hits, heuristic)
            if result is not None:
                llm_payload, llm_model = result

        return self._merge(
            message=message,
            customer_name=customer_name,
            hits=hits,
            heuristic=heuristic,
            llm_payload=llm_payload,
            llm_model=llm_model,
        )

    def analyze_deterministic(
        self,
        *,
        message: str,
        customer_name: str | None,
        articles: list[KnowledgeArticle],
    ) -> AnalysisResult:
        """Rule-based analysis only. Used for seeding and for offline demos."""
        prior_category, prior_intent = self.priors(message)
        hits = self.retrieve(
            message,
            articles,
            preferred_category=prior_category.value,
            hint_slugs=INTENT_ARTICLE_HINTS.get(prior_intent, ()),
        )
        heuristic = self._heuristic(message, customer_name, hits)
        return self._merge(
            message=message,
            customer_name=customer_name,
            hits=hits,
            heuristic=heuristic,
            llm_payload=None,
            llm_model="",
        )

    # -- heuristics ---------------------------------------------------------

    def _heuristic(self, message: str, customer_name: str | None, hits: list[RetrievedArticle]) -> HeuristicAnalysis:
        text = _normalize(message)
        tokens = _content_tokens(text)

        category, scores, matched = _classify(text, hits)
        sentiment = _detect_sentiment(text)
        intent = _detect_intent(text, category)
        flags = _escalation_flags(text, tokens, category, hits)
        priority = _priority(category, text, sentiment, flags)
        confidence = _confidence(scores, category, hits)

        requires_human = bool(flags)
        reason = " ".join(flag.reason for flag in flags) if flags else None
        draft = _compose_draft(
            message=message,
            customer_name=customer_name,
            category=category,
            intent=intent,
            sentiment=sentiment,
            hits=hits,
            flags=flags,
            requires_human=requires_human,
        )
        classification_reason = _classification_reason(category, scores, matched, hits, intent)

        return HeuristicAnalysis(
            category=category,
            priority=priority,
            intent=intent,
            sentiment=sentiment,
            classification_reason=classification_reason,
            confidence=confidence,
            flags=flags,
            draft_reply=draft,
            category_scores=scores,
            matched_terms=matched,
        )

    # -- LLM ----------------------------------------------------------------

    async def _call_llm(
        self,
        message: str,
        customer_name: str | None,
        hits: list[RetrievedArticle],
        heuristic: HeuristicAnalysis,
    ) -> tuple[LLMAnalysis, str] | None:
        system_prompt = _system_prompt()
        user_prompt = _user_prompt(message, customer_name, hits, heuristic)
        result = await self.llm.complete_json(system_prompt=system_prompt, user_prompt=user_prompt)
        if result is None:
            return None
        try:
            payload = LLMAnalysis.model_validate(result.data)
        except Exception as exc:  # noqa: BLE001 - invalid model output -> deterministic fallback
            logger.warning("Discarding invalid LLM analysis: %s", exc)
            self.llm.last_error = f"Invalid structured output: {type(exc).__name__}"
            return None
        if not payload.category or not payload.priority:
            logger.warning("Discarding LLM analysis without category/priority")
            return None
        return payload, result.model

    def _merge(
        self,
        *,
        message: str,
        customer_name: str | None,
        hits: list[RetrievedArticle],
        heuristic: HeuristicAnalysis,
        llm_payload: LLMAnalysis | None,
        llm_model: str,
    ) -> AnalysisResult:
        if llm_payload is None:
            flags = heuristic.flags
            return AnalysisResult(
                category=heuristic.category,
                priority=heuristic.priority,
                intent=heuristic.intent,
                sentiment=heuristic.sentiment,
                classification_reason=heuristic.classification_reason,
                confidence=heuristic.confidence,
                requires_human=bool(flags),
                escalation_reason=" ".join(flag.reason for flag in flags) if flags else None,
                risk_flags=[flag.label for flag in flags],
                suggested_action=_suggested_action(bool(flags)),
                draft_reply=_finalize_draft(heuristic.draft_reply),
                retrieved=hits,
                ai_mode="fallback",
                ai_provider=self.settings.llm_provider,
                ai_model="deterministic-analyst-v1",
            )

        guardrail_notes: list[str] = []

        # Category and priority: the model decides, but urgency can never be
        # downgraded below what the deterministic signals found.
        category = Category(llm_payload.category)
        priority = Priority(llm_payload.priority)
        if PRIORITY_ORDER.index(heuristic.priority) > PRIORITY_ORDER.index(priority):
            priority = heuristic.priority
            guardrail_notes.append(f"Priority raised to {priority.value} by deterministic urgency signals.")

        # Human review is a union of both engines - a missed escalation is the
        # expensive mistake, so the guardrail wins.
        llm_requires_human = llm_payload.requires_human and bool(
            llm_payload.escalation_reason or llm_payload.risk_flags
        )
        requires_human = bool(heuristic.flags) or llm_requires_human
        reasons: list[str] = []
        if heuristic.flags:
            reasons.extend(flag.reason for flag in heuristic.flags)
        if llm_requires_human and llm_payload.escalation_reason:
            if llm_payload.escalation_reason not in reasons:
                reasons.append(llm_payload.escalation_reason)
        if not hits and requires_human is False:
            requires_human = True
            reasons.append(
                "No knowledge base article supports this request, so the assistant must not answer from "
                "its own assumptions."
            )
            guardrail_notes.append("Escalated because retrieval returned no grounding article.")

        risk_flags = [flag.label for flag in heuristic.flags]
        for flag in llm_payload.risk_flags:
            if flag not in risk_flags:
                risk_flags.append(flag)

        draft = llm_payload.draft_reply
        if not draft:
            draft = heuristic.draft_reply
            guardrail_notes.append("LLM returned no draft; used the grounded template reply.")
        elif _has_commitment_risk(draft):
            draft = heuristic.draft_reply
            requires_human = True
            guardrail_notes.append("Discarded LLM draft that contained an unapproved commitment.")
            reasons.append(
                "Draft guardrail: the generated reply contained a commitment the assistant is not allowed "
                "to make, so it was replaced with a grounded draft."
            )
            risk_flags.append("Draft guardrail")

        if not hits:
            requires_human = True

        confidence = llm_payload.confidence
        if heuristic.matched_terms:
            confidence = round(min(0.97, max(0.35, confidence)), 2)

        return AnalysisResult(
            category=category,
            priority=priority,
            intent=llm_payload.intent or heuristic.intent,
            sentiment=Sentiment(llm_payload.sentiment),
            classification_reason=llm_payload.classification_reason or heuristic.classification_reason,
            confidence=confidence,
            requires_human=requires_human,
            escalation_reason=" ".join(dict.fromkeys(reasons)) if reasons else None,
            risk_flags=risk_flags,
            suggested_action=_suggested_action(requires_human),
            draft_reply=_finalize_draft(draft),
            retrieved=hits,
            ai_mode="llm",
            ai_provider=self.settings.llm_provider,
            ai_model=llm_model or self.settings.llm_model,
            guardrail_notes=guardrail_notes,
        )


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    lowered = text.lower().replace("\u2019", "").replace("'", "")
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def _content_tokens(text: str) -> list[str]:
    from .knowledge import STOPWORDS, TOKEN_RE, stem

    return [stem(t) for t in TOKEN_RE.findall(text) if t not in STOPWORDS and len(t) > 1]


def _classify(
    text: str, hits: list[RetrievedArticle]
) -> tuple[Category, dict[Category, int], list[str]]:
    scores: dict[Category, int] = {category: 0 for category in Category}
    matched: dict[Category, list[tuple[str, int]]] = {category: [] for category in Category}

    for category, terms in CATEGORY_TERMS.items():
        for term, weight in terms.items():
            if term in text:
                scores[category] += weight
                matched[category].append((term, weight))

    # Knowledge retrieval is a weak signal that breaks ties on short messages.
    for position, hit in enumerate(hits):
        try:
            category = Category(hit.article.category)
        except ValueError:
            continue
        scores[category] += max(1, 4 - position)
        matched[category].append((f"kb:{hit.article.slug}", max(1, 4 - position)))

    best = max(scores.values()) if scores else 0
    order = [Category.REFUND, Category.TECHNICAL, Category.SHIPPING, Category.BILLING, Category.GENERAL]
    winners = [category for category in order if scores.get(category, 0) == best and best > 0]
    category = winners[0] if winners else Category.GENERAL

    top_terms = sorted(matched[category], key=lambda item: item[1], reverse=True)
    terms = [term for term, _ in top_terms[:5]]
    return category, scores, terms


def _detect_sentiment(text: str) -> Sentiment:
    angry_hits = sum(1 for word in ANGRY_WORDS if word in text)
    frustrated_hits = sum(1 for word in FRUSTRATED_WORDS if word in text)
    exclamations = text.count("!")

    if angry_hits >= 2 or (angry_hits >= 1 and exclamations >= 2):
        return Sentiment.ANGRY
    if angry_hits >= 1:
        return Sentiment.ANGRY
    if frustrated_hits >= 2 or exclamations >= 3:
        return Sentiment.FRUSTRATED
    if frustrated_hits >= 1:
        return Sentiment.FRUSTRATED
    if any(word in text for word in POSITIVE_WORDS):
        return Sentiment.POSITIVE
    return Sentiment.NEUTRAL


def _detect_intent(text: str, category: Category) -> str:
    for pattern, label in INTENT_RULES.get(category, []):
        if re.search(pattern, text):
            return label
    return {
        Category.SHIPPING: "Shipping question",
        Category.REFUND: "Refund request",
        Category.BILLING: "Billing question",
        Category.TECHNICAL: "Technical issue",
        Category.GENERAL: "General inquiry",
    }[category]


def _priority(
    category: Category,
    text: str,
    sentiment: Sentiment,
    flags: list[RiskFlag],
) -> Priority:
    score = PRIORITY_BASE.get(category, 1)
    for phrase, weight in PRIORITY_SIGNALS:
        if phrase in text:
            score += weight
    if sentiment is Sentiment.ANGRY:
        score += 2
    elif sentiment is Sentiment.FRUSTRATED:
        score += 1
    if flags:
        score += 1

    if score >= 11:
        return Priority.URGENT
    if score >= 5:
        return Priority.HIGH
    if score >= 3:
        return Priority.MEDIUM
    return Priority.LOW


def _escalation_flags(
    text: str,
    tokens: list[str],
    category: Category,
    hits: list[RetrievedArticle],
) -> list[RiskFlag]:
    flags: list[RiskFlag] = []
    seen: set[str] = set()

    for rule in RISK_RULES:
        if rule.key in seen:
            continue
        if rule.pattern.search(text):
            flags.append(RiskFlag(rule.key, rule.label, rule.reason, rule.short_reason))
            seen.add(rule.key)

    if len(tokens) < 6:
        flags.append(
            RiskFlag(
                key="unclear_request",
                label="Unclear request",
                reason=(
                    "Unclear request: there is not enough detail to classify or answer safely, so a human "
                    "should ask a clarifying question."
                ),
                short_reason="the request is too vague to answer safely",
            )
        )
        seen.add("unclear_request")

    if not hits and "no_knowledge" not in seen:
        flags.append(
            RiskFlag(
                key="no_knowledge",
                label="No knowledge match",
                reason=(
                    "No knowledge base article answers this question, so the assistant must not invent a "
                    "policy or an outcome."
                ),
                short_reason="we do not have a documented answer",
            )
        )

    return flags


def _confidence(scores: dict[Category, int], category: Category, hits: list[RetrievedArticle]) -> float:
    ordered = sorted(scores.values(), reverse=True)
    top = ordered[0] if ordered else 0
    runner_up = ordered[1] if len(ordered) > 1 else 0
    if top == 0:
        return 0.3
    margin = (top - runner_up) / top
    confidence = 0.45 + margin * 0.35 + min(0.15, len(hits) * 0.05)
    return round(min(0.92, confidence), 2)


def _classification_reason(
    category: Category,
    scores: dict[Category, int],
    matched: list[str],
    hits: list[RetrievedArticle],
    intent: str,
) -> str:
    label = category.label
    if not matched:
        reason = f"No strong category signals were found, so the ticket defaults to {label}."
    else:
        readable = ", ".join(term for term in matched if not term.startswith("kb:"))
        kb_terms = [term[3:] for term in matched if term.startswith("kb:")]
        signal_text = f"Matched {label.lower()} signals: {readable}." if readable else ""
        reason = f"Detected intent '{intent}'. {signal_text}".strip()
        if kb_terms:
            reason += f" Closest knowledge articles: {', '.join(kb_terms)}."
    runner_up = sorted(
        ((score, item) for item, score in scores.items() if item is not category and score > 0),
        reverse=True,
    )
    if runner_up and runner_up[0][0] >= scores.get(category, 0) * 0.8:
        reason += f" Runner-up category: {runner_up[0][1].label}."
    return reason.strip()


def _trim_sentences(text: str, max_sentences: int = 2, max_chars: int = 320) -> str:
    """Keep whole sentences only - a reply must never end mid-clause."""
    text = re.sub(r"\s+", " ", text).strip()
    sentences = [sentence for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]
    if not sentences:
        return text
    selected = [sentences[0]]
    for sentence in sentences[1:max_sentences]:
        if len(" ".join(selected)) + len(sentence) + 1 > max_chars:
            break
        selected.append(sentence)
    return " ".join(selected).strip()


def _compose_draft(
    *,
    message: str,
    customer_name: str | None,
    category: Category,
    intent: str,
    sentiment: Sentiment,
    hits: list[RetrievedArticle],
    flags: list[RiskFlag],
    requires_human: bool,
) -> str:
    name = first_name(customer_name)
    greeting = f"Hi {name}," if name else "Hello,"

    if sentiment is Sentiment.ANGRY:
        empathy = "I am really sorry about this, and I understand why you are upset."
    elif sentiment is Sentiment.FRUSTRATED:
        empathy = "I am sorry for the trouble this has caused."
    else:
        empathy = "Thanks for reaching out."

    paragraphs = [greeting, f"{empathy} {INTENT_ACKS.get(intent, ACK_LINES[category])}".strip()]

    if hits:
        top = hits[0]
        excerpt = _trim_sentences(top.excerpt)
        paragraphs.append(f"From our article '{top.article.title}': {excerpt}")
    else:
        paragraphs.append(
            "I do not have a documented answer for this in our knowledge base, and I would rather not guess "
            "at a policy or an outcome."
        )

    if requires_human:
        short_reasons = [flag.short_reason for flag in flags]
        if short_reasons:
            reason_text = short_reasons[0] if len(short_reasons) == 1 else f"{short_reasons[0]} and {short_reasons[1]}"
        else:
            reason_text = "a decision the team needs to review"
        paragraphs.append(
            f"Because this involves {reason_text}, I have passed your ticket to a teammate to review before we "
            "confirm anything further. A human will follow up, usually within one business day."
        )
    else:
        paragraphs.append(INTENT_NEXT_STEPS.get(intent, NEXT_STEPS[category]))

    paragraphs.append("Best regards,\nNorthwind Support Team")
    return "\n\n".join(paragraphs)


def _suggested_action(requires_human: bool) -> str:
    return "Needs human review" if requires_human else "Draft ready for approval"


def _finalize_draft(draft: str) -> str:
    text = draft.replace("**", "").replace("__", "").strip()
    text = re.sub(r"^(subject|re):.*\n+", "", text, flags=re.IGNORECASE)
    return text.strip()


def _has_commitment_risk(draft: str) -> bool:
    lowered = draft.lower()
    return any(pattern.search(lowered) for pattern in COMMITMENT_PATTERNS)


def _system_prompt() -> str:
    categories = ", ".join(category.value for category in Category)
    priorities = ", ".join(priority.value for priority in Priority)
    return (
        "You are SupportPilot, the triage analyst for Northwind Supply Co.'s customer support team. "
        "You analyze one incoming customer message at a time for a human agent.\n\n"
        "Return exactly one JSON object and no surrounding prose. Required keys:\n"
        '{"category": string, "priority": string, "intent": string, "sentiment": string, '
        '"classification_reason": string, "confidence": number, "requires_human": boolean, '
        '"escalation_reason": string|null, "risk_flags": string[], "draft_reply": string}\n\n'
        f"category must be one of: {categories}.\n"
        f"priority must be one of: {priorities}.\n"
        "sentiment must be one of: positive, neutral, frustrated, angry.\n\n"
        "Grounding rules (critical):\n"
        "- The knowledge base excerpts in the user message are the only source of company policy.\n"
        "- Never invent order statuses, tracking events, delivery dates, refund approvals, payment states, "
        "amounts, or policies that are not in the excerpts.\n"
        "- If the excerpts do not answer the question, say the information is not available and set "
        "requires_human=true.\n"
        "- Never promise a refund, replacement, delivery date, compensation or account change. Describe the "
        "process and let a human confirm outcomes.\n\n"
        "Escalation rules: set requires_human=true for policy exceptions, refund or payment decisions, "
        "duplicate charges, missing/damaged parcels, security or account-access issues, legal or public "
        "escalation threats, blocking outages, unclear requests, or questions with no knowledge base support. "
        "explain why in escalation_reason.\n\n"
        "Writing rules for draft_reply:\n"
        "- Professional, warm, concise: 90-160 words, plain text, no markdown, no placeholders like [Order].\n"
        "- Address the customer by first name if provided, otherwise 'Hello,'.\n"
        "- Use at most two short factual sentences from the knowledge base and mention the article title.\n"
        "- Ask for information you actually need (order number, error code, charge date) instead of guessing.\n"
        "- If requires_human is true, say a teammate will review and follow up; do not promise an outcome or a "
        "deadline.\n"
        "- End with 'Best regards,' then 'Northwind Support Team'.\n"
    )


def _user_prompt(
    message: str,
    customer_name: str | None,
    hits: list[RetrievedArticle],
    heuristic: HeuristicAnalysis,
) -> str:
    if hits:
        context_blocks = []
        for position, hit in enumerate(hits, start=1):
            body = re.sub(r"\s+", " ", hit.article.content).strip()[:1100]
            context_blocks.append(
                f"[{position}] {hit.article.title} (category: {hit.article.category}, "
                f"relevance: {hit.normalized_score:.2f})\n{body}"
            )
        context = "\n\n".join(context_blocks)
    else:
        context = "No knowledge base article matched this message."

    return (
        f"Customer name: {customer_name or 'unknown'}\n"
        f"Customer message:\n\"\"\"\n{message.strip()}\n\"\"\"\n\n"
        f"Knowledge base excerpts:\n{context}\n\n"
        "Deterministic signals (hints only, correct them if the message says otherwise):\n"
        f"- keyword category: {heuristic.category.value}\n"
        f"- keyword priority: {heuristic.priority.value}\n"
        f"- detected sentiment: {heuristic.sentiment.value}\n"
        f"- rule-based escalation flags: {', '.join(flag.label for flag in heuristic.flags) or 'none'}\n\n"
        "Analyze the message and return the JSON object."
    )