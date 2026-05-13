from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    # null parent_id means it's a top-level comment; otherwise it's a reply
    parent_id = Column(Integer, ForeignKey("comments.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    author = relationship("User", back_populates="comments")
    post = relationship("Post", back_populates="comments")
    # parent_comment is many-to-one (this comment → its parent); remote_side tells SQLAlchemy
    # which column lives on the "one" side so it doesn't confuse both ends as one-to-many.
    parent_comment = relationship(
        "Comment",
        remote_side="Comment.id",
        foreign_keys=[parent_id],
        back_populates="replies",
    )
    replies = relationship(
        "Comment",
        foreign_keys=[parent_id],
        back_populates="parent_comment",
    )
