"""Administração simples: usuários, cursos e log de acesso (LGPD)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..constants import Role
from ..database import get_db
from ..models import AccessLog, Course, User
from ..schemas import CourseIn, UserIn
from ..security import hash_password, require_roles
from .auth import user_out

router = APIRouter(prefix="/api/admin", tags=["Administração"])
admin = Depends(require_roles(Role.ADMIN))


@router.get("/users")
def users(_: User = admin, db: Session = Depends(get_db)):
    return [user_out(u) for u in db.scalars(select(User).order_by(User.name))]


@router.post("/users", status_code=201)
def create_user(data: UserIn, _: User = admin, db: Session = Depends(get_db)):
    if not data.password:
        raise HTTPException(422, "Informe uma senha (mínimo 6 caracteres).")
    if data.role in (Role.DOCENTE, Role.COORDENADOR, Role.SUBSTITUTO) and not data.course_id:
        raise HTTPException(422, "Docentes e coordenadores precisam de um curso.")
    u = User(name=data.name, email=data.email.strip().lower(), password_hash=hash_password(data.password),
             role=data.role, course_id=data.course_id, active=data.active)
    db.add(u)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Já existe um usuário com este e-mail.")
    return user_out(u)


@router.put("/users/{uid}")
def update_user(uid: int, data: UserIn, _: User = admin, db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "Usuário não encontrado.")
    u.name, u.email, u.role, u.course_id, u.active = data.name, data.email.strip().lower(), data.role, data.course_id, data.active
    if data.password:
        u.password_hash = hash_password(data.password)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Já existe um usuário com este e-mail.")
    return user_out(u)


@router.get("/courses")
def courses(_: User = admin, db: Session = Depends(get_db)):
    return [dict(id=c.id, name=c.name) for c in db.scalars(select(Course).order_by(Course.name))]


@router.post("/courses", status_code=201)
def create_course(data: CourseIn, _: User = admin, db: Session = Depends(get_db)):
    c = Course(name=data.name.strip())
    db.add(c)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Curso já cadastrado.")
    return dict(id=c.id, name=c.name)


@router.get("/access-logs")
def access_logs(_: User = admin, db: Session = Depends(get_db)):
    rows = db.scalars(select(AccessLog).order_by(AccessLog.id.desc()).limit(200)).all()
    return [dict(id=l.id, user=l.user.name if l.user else "-", action=l.action, resource=l.resource, ip=l.ip, created_at=l.created_at) for l in rows]
