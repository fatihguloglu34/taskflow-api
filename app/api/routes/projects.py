from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_membership, require_role
from app.db import get_db
from app.models import (
    Project,
    ProjectMember,
    ProjectRole,
    Task,
    TaskPriority,
    TaskStatus,
    User,
)
from app.schemas.common import Page
from app.schemas.project import (
    MemberAdd,
    MemberOut,
    MemberRoleUpdate,
    ProjectCreate,
    ProjectOut,
    ProjectStats,
    ProjectUpdate,
)

router = APIRouter(prefix="/projects", tags=["Projects"])


def _project_out(project: Project, role: ProjectRole) -> ProjectOut:
    out = ProjectOut.model_validate(project)
    out.my_role = role
    return out


# ---------- Projeler ----------


@router.get("", response_model=Page[ProjectOut])
def list_projects(
    q: Optional[str] = Query(None, description="İsimde arama"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    stmt = (
        select(Project, ProjectMember.role)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == user.id)
    )
    if q:
        stmt = stmt.where(Project.name.ilike(f"%{q}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.execute(
        stmt.order_by(Project.created_at.desc(), Project.id.desc()).limit(limit).offset(offset)
    ).all()
    items = [_project_out(project, role) for project, role in rows]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectOut:
    project = Project(name=payload.name, description=payload.description)
    project.members.append(ProjectMember(user_id=user.id, role=ProjectRole.OWNER))
    db.add(project)
    db.commit()
    db.refresh(project)
    return _project_out(project, ProjectRole.OWNER)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    membership: ProjectMember = Depends(get_membership), db: Session = Depends(get_db)
) -> ProjectOut:
    return _project_out(db.get(Project, membership.project_id), membership.role)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    payload: ProjectUpdate,
    membership: ProjectMember = Depends(require_role(ProjectRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ProjectOut:
    project = db.get(Project, membership.project_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return _project_out(project, membership.role)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    membership: ProjectMember = Depends(require_role(ProjectRole.OWNER)),
    db: Session = Depends(get_db),
) -> Response:
    db.delete(db.get(Project, membership.project_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/stats", response_model=ProjectStats)
def project_stats(
    membership: ProjectMember = Depends(get_membership), db: Session = Depends(get_db)
) -> ProjectStats:
    pid = membership.project_id
    by_status = {s.value: 0 for s in TaskStatus}
    for s, count in db.execute(
        select(Task.status, func.count()).where(Task.project_id == pid).group_by(Task.status)
    ):
        by_status[s.value] = count

    by_priority = {p.value: 0 for p in TaskPriority}
    for p, count in db.execute(
        select(Task.priority, func.count()).where(Task.project_id == pid).group_by(Task.priority)
    ):
        by_priority[p.value] = count

    overdue = db.scalar(
        select(func.count()).where(
            Task.project_id == pid,
            Task.due_date < date.today(),
            Task.status != TaskStatus.DONE,
        )
    )
    total = sum(by_status.values())
    completion = round(by_status[TaskStatus.DONE.value] / total * 100, 1) if total else 0.0
    return ProjectStats(
        total_tasks=total,
        by_status=by_status,
        by_priority=by_priority,
        overdue=overdue,
        completion_rate=completion,
    )


# ---------- Üyeler ----------


def _get_member_or_404(db: Session, project_id: int, user_id: int) -> ProjectMember:
    member = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
        )
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Üye bulunamadı")
    return member


@router.get("/{project_id}/members", response_model=List[MemberOut])
def list_members(
    membership: ProjectMember = Depends(get_membership), db: Session = Depends(get_db)
):
    members = db.scalars(
        select(ProjectMember)
        .where(ProjectMember.project_id == membership.project_id)
        .order_by(ProjectMember.joined_at, ProjectMember.id)
    ).all()
    return [MemberOut.model_validate(m) for m in members]


@router.post(
    "/{project_id}/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED
)
def add_member(
    payload: MemberAdd,
    membership: ProjectMember = Depends(require_role(ProjectRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ProjectMember:
    if payload.role == ProjectRole.OWNER:
        raise HTTPException(status_code=400, detail="Bir projenin yalnızca bir sahibi olabilir")
    if payload.role == ProjectRole.ADMIN and membership.role != ProjectRole.OWNER:
        raise HTTPException(status_code=403, detail="Sadece proje sahibi admin atayabilir")

    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None:
        raise HTTPException(status_code=404, detail="Bu e-postaya sahip kullanıcı yok")
    exists = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == membership.project_id, ProjectMember.user_id == user.id
        )
    )
    if exists:
        raise HTTPException(status_code=409, detail="Kullanıcı zaten projede")

    member = ProjectMember(project_id=membership.project_id, user_id=user.id, role=payload.role)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.patch("/{project_id}/members/{user_id}", response_model=MemberOut)
def update_member_role(
    user_id: int,
    payload: MemberRoleUpdate,
    membership: ProjectMember = Depends(require_role(ProjectRole.OWNER)),
    db: Session = Depends(get_db),
) -> ProjectMember:
    if payload.role == ProjectRole.OWNER:
        raise HTTPException(status_code=400, detail="Sahiplik devri bu endpoint ile yapılamaz")
    member = _get_member_or_404(db, membership.project_id, user_id)
    if member.role == ProjectRole.OWNER:
        raise HTTPException(status_code=400, detail="Proje sahibinin rolü değiştirilemez")
    member.role = payload.role
    db.commit()
    db.refresh(member)
    return member


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    user_id: int,
    membership: ProjectMember = Depends(get_membership),
    db: Session = Depends(get_db),
) -> Response:
    """Admin/sahip üyeleri çıkarabilir; her üye kendisi projeden ayrılabilir."""
    member = _get_member_or_404(db, membership.project_id, user_id)
    if member.role == ProjectRole.OWNER:
        raise HTTPException(status_code=400, detail="Proje sahibi projeden çıkarılamaz")

    is_self = member.user_id == membership.user_id
    if not is_self:
        if membership.role == ProjectRole.MEMBER:
            raise HTTPException(status_code=403, detail="Üye çıkarmak için yetkiniz yok")
        if membership.role == ProjectRole.ADMIN and member.role == ProjectRole.ADMIN:
            raise HTTPException(status_code=403, detail="Admin, başka bir admini çıkaramaz")

    # Ayrılan üyeye atanmış görevler atanmamış hale gelir
    for task in db.scalars(
        select(Task).where(Task.project_id == membership.project_id, Task.assignee_id == user_id)
    ):
        task.assignee_id = None
    db.delete(member)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
