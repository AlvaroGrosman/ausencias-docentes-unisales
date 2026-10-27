"""Notificações internas (simuladas, in-app). Em produção poderia disparar e-mail/WhatsApp."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AbsenceRequest, Notification, User


def notify(db: Session, user_ids, req: AbsenceRequest, message: str, at=None):
    for uid in set(user_ids):
        n = Notification(user_id=uid, request_id=req.id, message=f"{req.protocol}: {message}")
        if at:
            n.created_at = at
        db.add(n)


def users_with_role(db: Session, role: str, course_id: int | None = None) -> list[int]:
    q = select(User.id).where(User.role == role, User.active.is_(True))
    if course_id is not None:
        q = q.where(User.course_id == course_id)
    return list(db.scalars(q))
