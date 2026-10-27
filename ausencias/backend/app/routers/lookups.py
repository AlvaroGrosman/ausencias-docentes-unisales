"""Lista de cursos para qualquer usuário autenticado (só id e nome)."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Course, User
from ..security import get_current_user

router = APIRouter(prefix="/api", tags=["Apoio"])


@router.get("/courses")
def courses(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [dict(id=c.id, name=c.name) for c in db.scalars(select(Course).order_by(Course.name))]
