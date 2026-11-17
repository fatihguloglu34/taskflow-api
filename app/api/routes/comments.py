from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_membership, get_project_task, has_role
from app.db import get_db
from app.models import Comment, ProjectMember, ProjectRole, Task, User
from app.schemas.comment import CommentCreate, CommentOut

router = APIRouter(prefix="/projects/{project_id}/tasks/{task_id}/comments", tags=["Comments"])


@router.get("", response_model=List[CommentOut])
def list_comments(task: Task = Depends(get_project_task), db: Session = Depends(get_db)):
    return db.scalars(
        select(Comment).where(Comment.task_id == task.id).order_by(Comment.created_at, Comment.id)
    ).all()


@router.post("", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(
    payload: CommentCreate,
    task: Task = Depends(get_project_task),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Comment:
    comment = Comment(task_id=task.id, author_id=user.id, content=payload.content)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: int,
    task: Task = Depends(get_project_task),
    membership: ProjectMember = Depends(get_membership),
    db: Session = Depends(get_db),
) -> Response:
    comment = db.get(Comment, comment_id)
    if comment is None or comment.task_id != task.id:
        raise HTTPException(status_code=404, detail="Yorum bulunamadı")
    if comment.author_id != membership.user_id and not has_role(membership, ProjectRole.ADMIN):
        raise HTTPException(status_code=403, detail="Bu yorumu silme yetkiniz yok")
    db.delete(comment)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
