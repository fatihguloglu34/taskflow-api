from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import hash_password
from app.db import get_db
from app.models import ProjectMember, Task, TaskStatus, User
from app.schemas.common import Page
from app.schemas.task import TaskOut
from app.schemas.user import UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
def read_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.password is not None:
        user.hashed_password = hash_password(payload.password)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me/tasks", response_model=Page[TaskOut])
def my_tasks(
    status: Optional[TaskStatus] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Bana atanmış ve hâlâ üyesi olduğum projelerdeki görevler."""
    stmt = (
        select(Task)
        .join(ProjectMember, ProjectMember.project_id == Task.project_id)
        .where(Task.assignee_id == user.id, ProjectMember.user_id == user.id)
    )
    if status is not None:
        stmt = stmt.where(Task.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(
        stmt.order_by(Task.due_date.is_(None), Task.due_date, Task.id).limit(limit).offset(offset)
    ).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}
