from datetime import date
from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_membership, get_project_task, has_role
from app.db import get_db
from app.models import ProjectMember, ProjectRole, Task, TaskPriority, TaskStatus, User
from app.schemas.common import Page
from app.schemas.task import TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["Tasks"])


class SortField(str, Enum):
    CREATED_AT = "created_at"
    DUE_DATE = "due_date"
    PRIORITY = "priority"
    TITLE = "title"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


PRIORITY_RANK = case(
    (Task.priority == TaskPriority.LOW, 1),
    (Task.priority == TaskPriority.MEDIUM, 2),
    (Task.priority == TaskPriority.HIGH, 3),
)


def _ensure_assignee_is_member(db: Session, project_id: int, assignee_id: Optional[int]) -> None:
    if assignee_id is None:
        return
    is_member = db.scalar(
        select(ProjectMember.id).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == assignee_id
        )
    )
    if not is_member:
        raise HTTPException(status_code=400, detail="Atanan kişi projenin üyesi olmalı")


@router.get("", response_model=Page[TaskOut])
def list_tasks(
    status_: Optional[TaskStatus] = Query(None, alias="status"),
    priority: Optional[TaskPriority] = None,
    assignee_id: Optional[int] = None,
    unassigned: bool = False,
    overdue: bool = False,
    q: Optional[str] = Query(None, description="Başlık ve açıklamada arama"),
    sort_by: SortField = SortField.CREATED_AT,
    order: SortOrder = SortOrder.DESC,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    membership: ProjectMember = Depends(get_membership),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Task).where(Task.project_id == membership.project_id)
    if status_ is not None:
        stmt = stmt.where(Task.status == status_)
    if priority is not None:
        stmt = stmt.where(Task.priority == priority)
    if assignee_id is not None:
        stmt = stmt.where(Task.assignee_id == assignee_id)
    if unassigned:
        stmt = stmt.where(Task.assignee_id.is_(None))
    if overdue:
        stmt = stmt.where(Task.due_date < date.today(), Task.status != TaskStatus.DONE)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(or_(Task.title.ilike(pattern), Task.description.ilike(pattern)))

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))

    column = {
        SortField.CREATED_AT: Task.created_at,
        SortField.DUE_DATE: Task.due_date,
        SortField.PRIORITY: PRIORITY_RANK,
        SortField.TITLE: Task.title,
    }[sort_by]
    ordering = [column.asc() if order == SortOrder.ASC else column.desc(), Task.id.desc()]
    if sort_by == SortField.DUE_DATE:
        ordering.insert(0, Task.due_date.is_(None))  # Tarihsiz görevler hep sonda

    items = db.scalars(stmt.order_by(*ordering).limit(limit).offset(offset)).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    membership: ProjectMember = Depends(get_membership),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Task:
    _ensure_assignee_is_member(db, membership.project_id, payload.assignee_id)
    task = Task(**payload.model_dump(), project_id=membership.project_id, created_by_id=user.id)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task: Task = Depends(get_project_task)) -> Task:
    return task


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    payload: TaskUpdate,
    task: Task = Depends(get_project_task),
    db: Session = Depends(get_db),
) -> Task:
    data = payload.model_dump(exclude_unset=True)
    if "assignee_id" in data:
        _ensure_assignee_is_member(db, task.project_id, data["assignee_id"])
    for field in ("title", "status", "priority"):
        if field in data and data[field] is None:
            raise HTTPException(status_code=422, detail=f"'{field}' boş bırakılamaz")
    for field, value in data.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task: Task = Depends(get_project_task),
    membership: ProjectMember = Depends(get_membership),
    db: Session = Depends(get_db),
) -> Response:
    """Görevi oluşturan kişi veya proje admin/sahibi silebilir."""
    if task.created_by_id != membership.user_id and not has_role(membership, ProjectRole.ADMIN):
        raise HTTPException(status_code=403, detail="Bu görevi silme yetkiniz yok")
    db.delete(task)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
