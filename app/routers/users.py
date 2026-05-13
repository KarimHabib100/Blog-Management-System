from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserResponse, UserUpdate
from app.core.dependencies import get_current_user, get_admin_user


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Return the currently logged-in user's profile."""
    return current_user


@router.put("/me", response_model=UserResponse)
def update_my_profile(
    updates: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update own profile. Regular users cannot change their role."""
    if updates.role is not None and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can change roles",
        )

    if updates.username:
        taken = db.query(User).filter(
            User.username == updates.username,
            User.id != current_user.id,
        ).first()
        if taken:
            raise HTTPException(status_code=400, detail="That username is already taken")
        current_user.username = updates.username

    if updates.email:
        taken = db.query(User).filter(
            User.email == updates.email,
            User.id != current_user.id,
        ).first()
        if taken:
            raise HTTPException(status_code=400, detail="That email is already in use")
        current_user.email = updates.email

    db.commit()
    db.refresh(current_user)
    logger.info(f"User {current_user.username} updated their profile")
    return current_user


# ── Admin-only endpoints ──────────────────────────────────────────────────────

@router.get("/", response_model=List[UserResponse])
def list_all_users(
    skip: int = 0,
    limit: int = 20,
    _admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """List all users. Admin only."""
    return db.query(User).offset(skip).limit(limit).all()


@router.put("/{user_id}", response_model=UserResponse)
def admin_update_user(
    user_id: int,
    updates: UserUpdate,
    _admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Update any user's data. Admin only."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for field, value in updates.model_dump(exclude_none=True).items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    logger.info(f"Admin updated user {user.username}")
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_user(
    user_id: int,
    _admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Delete a user. Admin only."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    logger.info(f"Admin deleted user id={user_id}")
