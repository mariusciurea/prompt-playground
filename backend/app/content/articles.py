"""Learn articles: Markdown files with a small `title`/`summary` header, loaded once."""

from dataclasses import dataclass
from functools import cache
from pathlib import Path

_LEARN_DIR = Path(__file__).parent / "learn"
PROMPTING_GUIDE_URL = "https://www.promptingguide.ai/techniques"


@dataclass(frozen=True, slots=True)
class Article:
    """A Learn article."""

    slug: str
    title: str
    summary: str
    body: str


def _parse(path: Path) -> Article:
    text = path.read_text(encoding="utf-8")
    _, header, body = text.split("---", 2)
    meta = dict(line.split(":", 1) for line in header.strip().splitlines())
    slug = path.stem.split("-", 1)[1]
    return Article(
        slug=slug,
        title=meta["title"].strip(),
        summary=meta["summary"].strip(),
        body=body.strip(),
    )


@cache
def all_articles() -> tuple[Article, ...]:
    """Return every article, ordered by file name."""
    return tuple(_parse(path) for path in sorted(_LEARN_DIR.glob("*.md")))


def get_article(slug: str) -> Article | None:
    """Return one article by slug."""
    return next((a for a in all_articles() if a.slug == slug), None)
