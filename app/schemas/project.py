from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import ProjectRole
from app.schemas.user import UserPublic


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=5000)


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=5000)


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    my_role: Optional[ProjectRole] = None


class MemberAdd(BaseModel):
    email: EmailStr
    role: ProjectRole = ProjectRole.MEMBER


class MemberRoleUpdate(BaseModel):
    role: ProjectRole


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user: UserPublic
    role: ProjectRole
    joined_at: datetime


class ProjectStats(BaseModel):
    total_tasks: int
    by_status: Dict[str, int]
    by_priority: Dict[str, int]
    overdue: int
    completion_rate: float
