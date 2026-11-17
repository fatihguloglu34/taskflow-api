"""Demo verisi olusturur.  Kullanim: python -m scripts.seed"""
from datetime import date, timedelta

from sqlalchemy import select

from app.core.security import hash_password
from app.db import Base, SessionLocal, engine
from app.models import Comment, Project, ProjectMember, ProjectRole, Task, TaskPriority, TaskStatus, User


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.scalar(select(User).where(User.email == "demo@taskflow.dev")):
        print("Demo verisi zaten var.")
        return

    demo = User(email="demo@taskflow.dev", full_name="Demo User", hashed_password=hash_password("demo12345"))
    ayse = User(email="ayse@taskflow.dev", full_name="Ayse Yilmaz", hashed_password=hash_password("demo12345"))
    db.add_all([demo, ayse])
    db.flush()

    project = Project(name="Mobil Uygulama v2", description="Yeni surum icin backend isleri")
    project.members = [
        ProjectMember(user_id=demo.id, role=ProjectRole.OWNER),
        ProjectMember(user_id=ayse.id, role=ProjectRole.ADMIN),
    ]
    db.add(project)
    db.flush()

    today = date.today()
    tasks = [
        Task(title="Login endpoint'i", status=TaskStatus.DONE, priority=TaskPriority.HIGH, assignee_id=demo.id),
        Task(title="Push bildirim servisi", status=TaskStatus.IN_PROGRESS, priority=TaskPriority.HIGH,
             assignee_id=ayse.id, due_date=today + timedelta(days=3)),
        Task(title="Rate limiting ekle", priority=TaskPriority.MEDIUM, due_date=today - timedelta(days=2)),
        Task(title="API dokumantasyonunu guncelle", priority=TaskPriority.LOW, assignee_id=demo.id),
    ]
    for t in tasks:
        t.project_id = project.id
        t.created_by_id = demo.id
    db.add_all(tasks)
    db.flush()

    db.add(Comment(task_id=tasks[1].id, author_id=ayse.id, content="FCM entegrasyonuna basladim."))
    db.commit()
    db.close()
    print("Demo verisi olusturuldu -> demo@taskflow.dev / demo12345")


if __name__ == "__main__":
    run()
