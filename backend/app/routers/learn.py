"""The Learn section: security best-practice articles (available without course access)."""

from fastapi import APIRouter

from app.auth.dependencies import CurrentUser
from app.content.articles import PROMPTING_GUIDE_URL, all_articles, get_article
from app.core.exceptions import NotFoundError
from app.data_models.common import Schema


class ArticleSummary(Schema):
    """An article's heading, for the table of contents."""

    slug: str
    title: str
    summary: str


class ArticleOut(ArticleSummary):
    """A full article."""

    body: str


class LearnIndexOut(Schema):
    """The Learn table of contents and external references."""

    articles: list[ArticleSummary]
    prompting_guide_url: str


router = APIRouter(prefix="/learn", tags=["learn"])


@router.get("")
async def index(_: CurrentUser) -> LearnIndexOut:
    """List the Learn articles."""
    return LearnIndexOut(
        articles=[
            ArticleSummary(slug=a.slug, title=a.title, summary=a.summary) for a in all_articles()
        ],
        prompting_guide_url=PROMPTING_GUIDE_URL,
    )


@router.get("/{slug}")
async def article(slug: str, _: CurrentUser) -> ArticleOut:
    """Return one Learn article."""
    found = get_article(slug)
    if found is None:
        raise NotFoundError("Article not found.")
    return ArticleOut(slug=found.slug, title=found.title, summary=found.summary, body=found.body)
