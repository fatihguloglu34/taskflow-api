from typing import Callable

from fastapi import Depends, HTTPException, Path, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db import get_db
from app.models import Project, ProjectMember, ProjectRole, Task, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

# Rol hiyerarşisi: yüksek sayı = daha fazla yetki
ROLE_LEVEL = {ProjectRole.MEMBER: 1, ProjectRole.ADMIN: 2, ProjectRole.OWNER: 3}


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kimlik doğrulanamadı",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_error
    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise credentials_error
    return user


def get_membership(
    project_id: int = Path(..., ge=1),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectMember:
    """Kullanıcının projedeki üyeliğini döner. Proje yoksa veya üye değilse 404.

    Üye olmayanlara 403 yerine 404 dönmek, projenin varlığını sızdırmamak içindir.
    """
    membership = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == user.id
        )
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")
    return membership


def require_role(min_role: ProjectRole) -> Callable[..., ProjectMember]:
    """Belirli bir minimum rol gerektiren dependency üretir."""

    def checker(membership: ProjectMember = Depends(get_membership)) -> ProjectMember:
        if ROLE_LEVEL[membership.role] < ROLE_LEVEL[min_role]:
            raise HTTPException(
                status_code=403, detail=f"Bu işlem için en az '{min_role.value}' rolü gerekli"
            )
        return membership

    return checker


def has_role(membership: ProjectMember, min_role: ProjectRole) -> bool:
    return ROLE_LEVEL[membership.role] >= ROLE_LEVEL[min_role]


def get_project_task(
    task_id: int = Path(..., ge=1),
    membership: ProjectMember = Depends(get_membership),
    db: Session = Depends(get_db),
) -> Task:
    task = db.get(Task, task_id)
    if task is None or task.project_id != membership.project_id:
        raise HTTPException(status_code=404, detail="Görev bulunamadı")
    return task


def get_project(membership: ProjectMember = Depends(get_membership), db: Session = Depends(get_db)) -> Project:
    return db.get(Project, membership.project_id)
