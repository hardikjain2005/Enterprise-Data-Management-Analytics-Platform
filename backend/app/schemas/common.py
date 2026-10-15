from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    # from_attributes=True lets Pydantic read SQLAlchemy objects directly
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    """Standard shape of every paginated list endpoint."""
    items: list[T]
    total: int
    page: int
    page_size: int


class Message(BaseModel):
    message: str
