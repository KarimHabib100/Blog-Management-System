from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from loguru import logger

from app.database import get_db
from app.models.user import User, UserRole
from app.models.post import Post
from app.schemas.post import PostCreate, PostUpdate, PostResponse, PostListResponse
from app.core.dependencies import get_current_user, require_role
from app.cache.redis_cache import cache_get, cache_set, cache_delete, cache_delete_pattern


router = APIRouter(prefix="/posts", tags=["Posts"])


@router.get("/", response_model=PostListResponse)
def get_posts(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=50, description="Results per page"),
    db: Session = Depends(get_db),
):
    """Get all posts with pagination. Public endpoint — no auth required."""
    cache_key = f"posts:p{page}:n{per_page}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    offset = (page - 1) * per_page
    total = db.query(Post).count()
    posts = (
        db.query(Post)
        .order_by(Post.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    result = PostListResponse(
        total=total,
        page=page,
        per_page=per_page,
        posts=posts,
    ).model_dump()

    cache_set(cache_key, result)
    return result


@router.get("/{post_id}", response_model=PostResponse)
def get_post(post_id: int, db: Session = Depends(get_db)):
    """Get a single post by ID. Public endpoint."""
    cache_key = f"post:{post_id}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    result = PostResponse.model_validate(post).model_dump()
    cache_set(cache_key, result)
    return post


@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    post_data: PostCreate,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.author)),
    db: Session = Depends(get_db),
):
    """Create a new post. Authors and admins only."""
    post = Post(
        title=post_data.title,
        content=post_data.content,
        author_id=current_user.id,
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    cache_delete_pattern("posts:p*")
    logger.info(f"Post created by {current_user.username}: '{post.title}'")
    return post


@router.put("/{post_id}", response_model=PostResponse)
def update_post(
    post_id: int,
    post_data: PostUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a post. Authors can only edit their own; admins can edit any."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if post.author_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own posts",
        )

    if post_data.title is not None:
        post.title = post_data.title
    if post_data.content is not None:
        post.content = post_data.content

    db.commit()
    db.refresh(post)

    cache_delete(f"post:{post_id}")
    cache_delete_pattern("posts:p*")

    logger.info(f"Post {post_id} updated by {current_user.username}")
    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a post. Authors can delete their own; admins can delete any."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if current_user.role != UserRole.admin and post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own posts",
        )

    db.delete(post)
    db.commit()

    cache_delete(f"post:{post_id}")
    cache_delete_pattern("posts:p*")

    logger.info(f"Post {post_id} deleted by {current_user.username}")
