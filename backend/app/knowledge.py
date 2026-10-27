"""Lightweight BM25 retrieval over the stored knowledge base.

The corpus is small (dozens of articles), so an in-process BM25 implementation is
faster and simpler than a vector store, and it keeps the hackathon build free of
external services. Query terms are expanded with a small, high-precision synonym
map at reduced weight, so "parcel not delivered" still finds a shipping article
without dragging every refund question toward the address-change article.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from .models import KnowledgeArticle

TOKEN_RE = re.compile(r"[a-z0-9]+")

STOPWORDS = {
    "a", "about", "after", "again", "all", "also", "am", "an", "and", "any", "are", "as", "at",
    "be", "because", "been", "before", "being", "but", "by", "can", "could", "did", "do", "does",
    "doing", "done", "for", "from", "get", "got", "had", "has", "have", "having", "he", "her",
    "here", "him", "his", "how", "i", "if", "in", "into", "is", "it", "its", "just", "me", "my",
    "no", "not", "now", "of", "on", "once", "only", "or", "other", "our", "out", "over", "please",
    "so", "some", "still", "such", "than", "that", "the", "their", "them", "then", "there",
    "these", "they", "this", "those", "through", "to", "too", "up", "us", "very", "was", "we",
    "were", "what", "when", "where", "which", "while", "who", "why", "will", "with", "would",
    "you", "your", "yours", "hi", "hello", "hey", "thanks", "thank", "regards", "dear", "sir",
    "madam", "im", "ive", "dont", "cant", "didnt", "doesnt", "isnt", "wasnt", "werent",
    "wont", "wouldnt", "couldnt", "shouldnt", "ur", "u", "like", "need", "want", "know", "make",
}

SYNONYM_GROUPS: list[tuple[str, ...]] = [
    ("refund", "reimbursement", "reimburse", "cashback"),
    ("return", "rma", "exchange"),
    ("shipping", "shipment", "delivery", "dispatch", "courier", "carrier"),
    ("parcel", "package", "box"),
    ("tracking", "track"),
    ("delayed", "delay", "late", "stuck", "overdue"),
    ("missing", "lost", "stolen", "undelivered"),
    ("damaged", "broken", "cracked", "defective", "faulty"),
    ("billing", "invoice", "receipt", "charge", "transaction"),
    ("payment", "pay", "paid", "card", "declined", "decline", "checkout"),
    ("subscription", "membership", "plan", "renewal", "renew"),
    ("technical", "error", "bug", "issue", "glitch", "crash", "freeze"),
    ("login", "signin", "password", "locked", "authentication"),
    ("app", "application", "dashboard", "platform", "portal", "website"),
    ("install", "update", "upgrade", "download"),
    ("cancel", "cancellation", "terminate"),
    ("warranty", "guarantee", "coverage"),
    ("exception", "waive", "waiver", "goodwill"),
]


def stem(token: str) -> str:
    """A deliberately small suffix stemmer (good enough for support vocabulary)."""
    if len(token) <= 4:
        return token
    if token.endswith("ies") and len(token) > 5:
        token = token[:-3] + "y"
    for _ in range(2):
        for suffix in (
            "ational", "ations", "ation", "ments", "ment", "ings", "ing", "ied",
            "ers", "er", "ed", "es", "al",
        ):
            if token.endswith(suffix) and len(token) - len(suffix) >= 4:
                token = token[: -len(suffix)]
                break
        else:
            if token.endswith("s") and not token.endswith(("ss", "us", "is", "as")) and len(token) >= 4:
                token = token[:-1]
                break
            break
    if token.endswith("e") and len(token) > 4:
        token = token[:-1]
    if len(token) > 3 and token[-1] == token[-2] and token[-1] not in "aeiouls":
        token = token[:-1]
    return token


SYNONYMS: dict[str, set[str]] = {}
for group in SYNONYM_GROUPS:
    stems = {stem(word) for word in group}
    for word in group:
        SYNONYMS.setdefault(stem(word), set()).update(stems - {stem(word)})

_URL_RE = re.compile(r"https?://\S+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def base_tokens(text: str) -> list[str]:
    cleaned = text.lower().replace("'", "").replace("\u2019", "")
    return [
        stem(token)
        for token in TOKEN_RE.findall(cleaned)
        if token not in STOPWORDS and len(token) > 1
    ]


def expand_token(token: str) -> set[str]:
    return SYNONYMS.get(token, set())


def tokenize(text: str, *, expand: bool = False) -> list[str]:
    tokens = base_tokens(text)
    if not expand:
        return tokens
    expanded = list(tokens)
    for token in tokens:
        for synonym in expand_token(token):
            if synonym not in expanded:
                expanded.append(synonym)
    return expanded


def weighted_query_terms(query: str) -> Counter[str]:
    """Original query words weigh 1.0, synonym expansions only 0.35."""
    base = base_tokens(query)
    weights: Counter[str] = Counter()
    for token in base:
        weights[token] += 1.0
    for token in base:
        for synonym in expand_token(token):
            if synonym not in weights:
                weights[synonym] = 0.35
    return weights


@dataclass
class RetrievedArticle:
    article: KnowledgeArticle
    score: float
    normalized_score: float
    excerpt: str

    def as_dict(self) -> dict:
        return {
            "id": self.article.id,
            "slug": self.article.slug,
            "title": self.article.title,
            "category": self.article.category,
            "summary": self.article.summary,
            "score": round(self.normalized_score, 3),
            "excerpt": self.excerpt,
        }


class KnowledgeIndex:
    """In-memory BM25 index built from the current article rows."""

    def __init__(self, articles: list[KnowledgeArticle], *, k1: float = 1.4, b: float = 0.75) -> None:
        self.articles = articles
        self.k1 = k1
        self.b = b
        self._term_freqs: list[Counter[str]] = []
        self._doc_lengths: list[int] = []

        for article in articles:
            # Title and tags repeat so they outweigh body prose, while still
            # being ordinary tokens rather than a separate scoring channel.
            weighted = (
                base_tokens(article.title) * 4
                + [token for tag in (article.tags or []) for token in base_tokens(tag)] * 3
                + base_tokens(article.summary)
                + base_tokens(article.content)
            )
            counts = Counter(weighted)
            self._term_freqs.append(counts)
            self._doc_lengths.append(len(weighted))

        self._avg_length = (sum(self._doc_lengths) / len(self._doc_lengths)) if self._doc_lengths else 0.0
        self._doc_freq: Counter[str] = Counter()
        for counts in self._term_freqs:
            self._doc_freq.update(counts.keys())

    def _idf(self, term: str) -> float:
        total = len(self._term_freqs)
        df = self._doc_freq.get(term, 0)
        return math.log(1 + (total - df + 0.5) / (df + 0.5))

    def search(
        self,
        query: str,
        *,
        top_k: int = 3,
        min_score: float = 0.6,
        preferred_category: str | None = None,
        hint_slugs: tuple[str, ...] | set[str] = (),
    ) -> list[RetrievedArticle]:
        if not self.articles:
            return []
        query_terms = weighted_query_terms(query)
        if not query_terms:
            return []

        hints = set(hint_slugs)
        raw_query_terms = set(base_tokens(query))
        scored: list[tuple[float, int]] = []
        for index, counts in enumerate(self._term_freqs):
            length = self._doc_lengths[index] or 1
            score = 0.0
            for term, weight in query_terms.items():
                freq = counts.get(term, 0)
                if not freq:
                    continue
                numerator = freq * (self.k1 + 1)
                denominator = freq + self.k1 * (1 - self.b + self.b * length / (self._avg_length or 1))
                score += weight * self._idf(term) * numerator / denominator
            if score < min_score:
                continue

            article = self.articles[index]
            headline_terms = set(base_tokens(f"{article.title} {article.summary}"))
            headline_overlap = len(raw_query_terms & headline_terms)
            # Reward documents whose title or summary actually names the problem.
            score *= 1 + 0.16 * headline_overlap
            # Category and intent priors keep a generic word ("order", "return")
            # from outranking the article that owns the topic.
            if preferred_category and article.category == preferred_category:
                score *= 1.25
            if article.slug in hints:
                score *= 1.9
            scored.append((score, index))

        if not scored:
            return []

        scored.sort(reverse=True)
        top = scored[:top_k]
        max_score = top[0][0]
        results: list[RetrievedArticle] = []
        for raw_score, index in top:
            article = self.articles[index]
            results.append(
                RetrievedArticle(
                    article=article,
                    score=raw_score,
                    normalized_score=round(min(1.0, raw_score / max_score), 3),
                    excerpt=best_excerpt(article.content, query),
                )
            )
        return results


def best_excerpt(content: str, query: str, *, max_chars: int = 460) -> str:
    """Return whole sentences of an article that best answer the query."""
    plain = _URL_RE.sub("", content).strip()
    sentences = [sentence.strip() for sentence in _SENTENCE_SPLIT_RE.split(plain) if sentence.strip()]
    if not sentences:
        return plain[:max_chars]

    query_terms = set(base_tokens(query))
    best_index = 0
    best_overlap = -1.0
    for index, sentence in enumerate(sentences):
        overlap = len(query_terms & set(base_tokens(sentence)))
        if overlap > best_overlap:
            best_overlap = overlap
            best_index = index

    excerpt = sentences[best_index]
    for neighbour in (best_index + 1, best_index - 1):
        if not (0 <= neighbour < len(sentences)):
            continue
        if len(excerpt) + len(sentences[neighbour]) + 1 > max_chars:
            continue
        # Only pull in a neighbour that also relates to the question; otherwise
        # the excerpt starts with an unrelated policy sentence.
        if not (query_terms & set(base_tokens(sentences[neighbour]))):
            # A lead sentence is often a heading-like summary ("We ship to 40
            # countries..."), so allow its immediate continuation once.
            if not (neighbour == best_index + 1 and best_index == 0):
                continue
        excerpt = (
            f"{excerpt} {sentences[neighbour]}"
            if neighbour > best_index
            else f"{sentences[neighbour]} {excerpt}"
        )
    # Never cut a sentence in half: an incomplete clause is worse than a longer excerpt.
    return excerpt.strip()