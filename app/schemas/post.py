from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator
from app.schemas.user import UserResponse


class PostCreate(BaseModel):
    title: str
    content: str

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty")
        return v

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v


class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    author_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    author: UserResponse

    model_config = {"from_attributes": True}


class PostListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    posts: list[PostResponse]
