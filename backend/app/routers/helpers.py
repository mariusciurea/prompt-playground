"""Shared helpers for routers: pagination parameters."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query


@dataclass(frozen=True, slots=True)
class Pagination:
    """Bounded limit/offset parameters (large pages make scraping easy)."""

    limit: int
    offset: int


def _pagination(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
) -> Pagination:
    return Pagination(limit=limit, offset=offset)


PaginationDep = Annotated[Pagination, Depends(_pagination)]
