from typing import Annotated, TypeVar

from fastapi import Depends
from pydantic import BaseModel, Field
from sqlmodel import SQLModel


T = TypeVar("T", bound=SQLModel)

MAX_RESULTS_PER_PAGE = 50


class PaginationModel(BaseModel):
    page: int = Field(1, ge=1, description="Page number (>=1)")
    limit: int = Field(30, ge=1, le=MAX_RESULTS_PER_PAGE, description="Items per page")

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.limit


Paginated = Annotated[PaginationModel, Depends()]
