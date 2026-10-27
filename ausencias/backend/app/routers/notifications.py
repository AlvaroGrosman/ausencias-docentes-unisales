from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Notification, User
from ..security import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["Notificações"])


@router.get("")
def list_notifications(u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Notification).where(Notification.user_id == u.id).order_by(Notification.id.desc()).limit(100)).all()
    return dict(unread=sum(1 for n in rows if not n.read),
                items=[dict(id=n.id, request_id=n.request_id, message=n.message, read=n.read, created_at=n.created_at) for n in rows])


@router.post("/read-all")
def read_all(u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(update(Notification).where(Notification.user_id == u.id).values(read=True))
    db.commit()
    return {"ok": True}


@router.post("/{nid}/read")
def read_one(nid: int, u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.get(Notification, nid)
    if not n or n.user_id != u.id:
        raise HTTPException(404, "Notificação não encontrada.")
    n.read = True
    db.commit()
    return {"ok": True}
