"""Auditoria: histórico de eventos da solicitação e log de acesso a dados sensíveis (LGPD)."""
from sqlalchemy.orm import Session

from ..models import AccessLog, AbsenceRequest, RequestEvent, User
from ..utils import now


def log_event(db: Session, req: AbsenceRequest, user: User | None, action: str,
              from_status: str | None, to_status: str, note: str | None = None, at=None):
    db.add(RequestEvent(request_id=req.id, user_id=user.id if user else None, action=action,
                        from_status=from_status, to_status=to_status, note=note, created_at=at or now()))


def log_access(db: Session, user: User, action: str, resource: str, ip: str | None):
    db.add(AccessLog(user_id=user.id, action=action, resource=resource, ip=ip, created_at=now()))
    db.commit()
