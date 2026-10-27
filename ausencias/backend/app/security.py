"""Autenticação JWT + senhas com hash bcrypt + controle de acesso por perfil."""
import os
from datetime import timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .utils import now

SECRET = os.getenv("JWT_SECRET", "dev-secret-troque-em-producao-chave-longa-32bytes")
ALGORITHM = "HS256"
bearer = HTTPBearer(auto_error=False)


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_password(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except ValueError:
        return False


def create_token(user: User) -> str:
    payload = {"sub": str(user.id), "role": user.role, "exp": now() + timedelta(hours=8)}
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not cred:
        raise HTTPException(401, "Não autenticado.")
    try:
        data = jwt.decode(cred.credentials, SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(401, "Sessão inválida ou expirada. Faça login novamente.")
    user = db.get(User, int(data["sub"]))
    if not user or not user.active:
        raise HTTPException(401, "Usuário inexistente ou inativo.")
    return user


def require_roles(*roles: str):
    """Dependência de rota: só deixa passar os perfis informados (protege no backend)."""
    def dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Seu perfil não tem permissão para esta operação.")
        return user
    return dep


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "desconhecido"
