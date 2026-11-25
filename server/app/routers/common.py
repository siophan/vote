from typing import Annotated

from fastapi import Query

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


class Pagination:
    def __init__(
        self,
        page: Annotated[int, Query()] = 1,
        page_size: Annotated[int, Query()] = DEFAULT_PAGE_SIZE,
    ):
        self.page = max(1, page)
        self.page_size = min(MAX_PAGE_SIZE, max(1, page_size))

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
