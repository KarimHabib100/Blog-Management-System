from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from loguru import logger

from app.database import get_db
from app.models.user import User, UserRole
from app.models.post import Post
from app.models.comment import Comment
from app.schemas.comment import CommentCreate, CommentUpdate, CommentResponse, CommentListResponse
from app.core.dependencies import get_current_user
from app.cache.redis_cache import cache_get, cache_set, cache_delete_pattern


router = APIRouter(prefix="/posts/{post_id}/comments", tags=["Comments"])


def _get_post_or_404(post_id: int, db: Session) -> Post:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


def _build_comment_dict(comment: Comment) -> dict:
    """Serialize a comment ORM object to a plain dict (no nested replies yet)."""
    return {
        "id": comment.id,
        "content": comment.content,
        "author_id": comment.author_id,
        "post_id": comment.post_id,
        "parent_id": comment.parent_id,
        "created_at": comment.created_at,
        "author": {
            "id": comment.author.id,
            "username": comment.author.username,
            "email": comment.author.email,
            "role": comment.author.role,
            "is_active": comment.author.is_active,
            "created_at": comment.author.created_at,
        },
        "replies": [],
    }


def _build_comment_tree(all_comments: list[Comment]) -> list[dict]:
    """
    Turn a flat list of Comment rows into a nested tree.
    Top-level comments have parent_id = None; replies nest under their parent.
    """
    by_id = {c.id: _build_comment_dict(c) for c in all_comments}
    roots = []

    for comment in all_comments:
        node = by_id[comment.id]
        if comment.parent_id is None:
            roots.append(node)
        elif comment.parent_id in by_id:
            by_id[comment.parent_id]["replies"].append(node)

    return roots


@router.get("/", response_model=CommentListResponse)
def get_comments(
    post_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get all top-level comments for a post (with nested replies). Public."""
    _get_post_or_404(post_id, db)

    cache_key = f"comments:post:{post_id}:p{page}:n{per_page}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    # count only top-level comments for pagination
    total = db.query(Comment).filter(
        Comment.post_id == post_id,
        Comment.parent_id == None,  # noqa: E711
    ).count()

    # load every comment for this post in one shot (replies included)
    all_comments = (
        db.query(Comment)
        .filter(Comment.post_id == post_id)
        .options(joinedload(Comment.author))
        .order_by(Comment.created_at.asc())
        .all()
    )

    # separate top-level, paginate, then attach their replies
    top_level = [c for c in all_comments if c.parent_id is None]
    paginated_ids = {c.id for c in top_level[(page - 1) * per_page: page * per_page]}

    # keep only comments that belong to the paginated top-level set
    relevant = [c for c in all_comments if c.id in paginated_ids or c.parent_id in paginated_ids]
    tree = _build_comment_tree(relevant)

    result = {"total": total, "page": page, "per_page": per_page, "comments": tree}
    cache_set(cache_key, result)
    return result


@router.post("/", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(
    post_id: int,
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a comment to a post. Any authenticated user can comment."""
    _get_post_or_404(post_id, db)

    if comment_data.parent_id is not None:
        parent = db.query(Comment).filter(
            Comment.id == comment_data.parent_id,
            Comment.post_id == post_id,
        ).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent comment not found")

    comment = Comment(
        content=comment_data.content,
        author_id=current_user.id,
        post_id=post_id,
        parent_id=comment_data.parent_id,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    cache_delete_pattern(f"comments:post:{post_id}:*")
    logger.info(f"Comment added to post {post_id} by {current_user.username}")

    return _build_comment_dict(comment)


@router.put("/{comment_id}", response_model=CommentResponse)
def update_comment(
    post_id: int,
    comment_id: int,
    comment_data: CommentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Edit a comment. Users can only edit their own; admins can edit any."""
    comment = db.query(Comment).filter(
        Comment.id == comment_id,
        Comment.post_id == post_id,
    ).first()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if comment.author_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own comments",
        )

    comment.content = comment_data.content
    db.commit()
    db.refresh(comment)

    cache_delete_pattern(f"comments:post:{post_id}:*")
    logger.info(f"Comment {comment_id} edited by {current_user.username}")

    return _build_comment_dict(comment)


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    post_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a comment. Users delete their own; admins can delete any."""
    comment = db.query(Comment).filter(
        Comment.id == comment_id,
        Comment.post_id == post_id,
    ).first()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if current_user.role != UserRole.admin and comment.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own comments",
        )

    db.delete(comment)
    db.commit()

    cache_delete_pattern(f"comments:post:{post_id}:*")
    logger.info(f"Comment {comment_id} deleted by {current_user.username}")
