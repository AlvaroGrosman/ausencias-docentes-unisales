from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..constants import ROLE_LABELS, STATUS_LABELS, TYPE_LABELS
from ..database import get_db
from ..models import User
from ..schemas import LoginIn
from ..security import create_token, get_current_user, verify_password

router = APIRouter(prefix="/api", tags=["Autenticação"])


def user_out(u: User) -> dict:
    return dict(id=u.id, name=u.name, email=u.email, role=u.role, role_label=ROLE_LABELS[u.role],
                course_id=u.course_id, course_name=u.course_name, active=u.active)


@router.post("/auth/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.strip().lower()))
    if not user or not user.active or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "E-mail ou senha incorretos.")
    return {"token": create_token(user), "user": user_out(user)}


@router.get("/auth/me")
def me(user: User = Depends(get_current_user)):
    return user_out(user)


@router.get("/meta")
def meta():
    """Rótulos em português para o frontend (fonte única de verdade)."""
    return dict(status=STATUS_LABELS, types=TYPE_LABELS, roles=ROLE_LABELS)
