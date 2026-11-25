"""Conexão com o banco de dados PostgreSQL.

A URL de conexão vem da variável de ambiente DATABASE_URL, que pode ser definida
no arquivo backend/.env (veja backend/.env.example). O SQLAlchemy continua sendo a
camada de acesso: ele traduz os modelos Python em tabelas e consultas SQL, e o
driver psycopg é quem conversa com o PostgreSQL.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DEFAULT_URL = "postgresql+psycopg://ausencias:ausencias@localhost:5432/ausencias"
DB_URL = os.getenv("DATABASE_URL", DEFAULT_URL)

# pool_pre_ping: testa a conexão antes de usá-la (evita erro se o PostgreSQL reiniciar).
engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
