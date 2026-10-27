"""Knowledge base browsing and retrieval preview."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..domain import Category
from ..knowledge import KnowledgeIndex
from ..models import KnowledgeArticle
from ..schemas import (
    KnowledgeArticleOut,
    KnowledgeListResponse,
    KnowledgeSearchHit,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from ..serializers import article_out
from ..service import list_articles

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("", response_model=KnowledgeListResponse)
def list_endpoint(
    session: Session = Depends(get_db),
    q: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None),
) -> dict:
    if category and category not in {item.value for item in Category}:
        raise HTTPException(status_code=422, detail=f"Unknown category '{category}'")

    articles = list_articles(session, search=q, category=category)
    # Category pills describe the whole corpus, so they need an aggregate over
    # all articles rather than a second full row fetch.
    counts = {
        str(value): int(count)
        for value, count in session.execute(
            select(KnowledgeArticle.category, func.count()).group_by(KnowledgeArticle.category)
        ).all()
    }
    return {
        "items": [article_out(article) for article in articles],
        "total": len(articles),
        "by_category": {category_item.value: counts.get(category_item.value, 0) for category_item in Category},
    }


@router.get("/{slug}", response_model=KnowledgeArticleOut)
def get_endpoint(slug: str, session: Session = Depends(get_db)) -> dict:
    article = session.scalars(select(KnowledgeArticle).where(KnowledgeArticle.slug == slug)).first()
    if article is None:
        raise HTTPException(status_code=404, detail=f"Article '{slug}' does not exist")
    return article_out(article)


@router.post("/search", response_model=KnowledgeSearchResponse)
def search_endpoint(payload: KnowledgeSearchRequest, session: Session = Depends(get_db)) -> dict:
    articles = list(session.scalars(select(KnowledgeArticle)).all())
    hits = KnowledgeIndex(articles).search(payload.query, top_k=payload.top_k)
    return {
        "query": payload.query,
        "hits": [
            {
                "slug": hit.article.slug,
                "title": hit.article.title,
                "category": hit.article.category,
                "summary": hit.article.summary,
                "score": hit.normalized_score,
                "excerpt": hit.excerpt,
            }
            for hit in hits
        ],
    }