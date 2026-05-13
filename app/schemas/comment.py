from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel
from app.schemas.user import UserResponse


class CommentCreate(BaseModel):
    content: str
    parent_id: Optional[int] = None


class CommentUpdate(BaseModel):
    content: str


class CommentResponse(BaseModel):
    id: int
    content: str
    author_id: int
    post_id: int
    parent_id: Optional[int] = None
    created_at: datetime
    author: UserResponse
    replies: list["CommentResponse"] = []

    model_config = {"from_attributes": True}


# needed because CommentResponse references itself
CommentResponse.model_rebuild()


class CommentListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    comments: list[CommentResponse]
