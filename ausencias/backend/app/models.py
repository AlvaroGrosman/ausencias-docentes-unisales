"""Modelo de dados (SQLAlchemy 2.x)."""
from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .utils import now


class Course(Base):
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(30))
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    course: Mapped["Course | None"] = relationship()

    @property
    def course_name(self):
        return self.course.name if self.course else None


class AbsenceRequest(Base):
    """Solicitação de ausência — o 'formulário impresso' digitalizado."""
    __tablename__ = "absence_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    type: Mapped[str] = mapped_column(String(20))          # PROGRAMADA | NAO_PROGRAMADA
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    subjects: Mapped[str] = mapped_column(Text)            # disciplinas/turmas afetadas
    reason: Mapped[str] = mapped_column(Text)              # dado sensível (LGPD)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachment_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    attachment_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    suggested_substitute_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    substitute_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    substitute_status: Mapped[str | None] = mapped_column(String(10), nullable=True)  # PENDENTE | ACEITA
    status: Mapped[str] = mapped_column(String(40), default="RASCUNHO", index=True)
    returns_count: Mapped[int] = mapped_column(Integer, default=0)  # devoluções = proxy de retrabalho
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    teacher: Mapped[User] = relationship(foreign_keys=[teacher_id])
    course: Mapped[Course] = relationship()
    suggested_substitute: Mapped[User | None] = relationship(foreign_keys=[suggested_substitute_id])
    substitute: Mapped[User | None] = relationship(foreign_keys=[substitute_id])
    events: Mapped[list["RequestEvent"]] = relationship(order_by="RequestEvent.id", back_populates="request")
    signatures: Mapped[list["Signature"]] = relationship(order_by="Signature.id", back_populates="request")

    @property
    def protocol(self):
        return f"AUS-{(self.created_at or now()).year}-{self.id:04d}"

    @property
    def days(self):
        return (self.end_date - self.start_date).days + 1


class RequestEvent(Base):
    """Histórico/auditoria: quem, quando, ação, status anterior -> novo, observação."""
    __tablename__ = "request_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("absence_requests.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)  # None = Sistema
    action: Mapped[str] = mapped_column(String(40))
    from_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_status: Mapped[str] = mapped_column(String(40))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    request: Mapped[AbsenceRequest] = relationship(back_populates="events")
    user: Mapped[User | None] = relationship()


class Notification(Base):
    """Notificação interna (in-app, simulada — não envia e-mail)."""
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    request_id: Mapped[int | None] = mapped_column(ForeignKey("absence_requests.id"), nullable=True)
    message: Mapped[str] = mapped_column(String(300))
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Signature(Base):
    __tablename__ = "signatures"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("absence_requests.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(30))
    signed_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    ip: Mapped[str] = mapped_column(String(60))
    content_hash: Mapped[str] = mapped_column(String(64))
    algorithm: Mapped[str] = mapped_column(String(40))
    request: Mapped[AbsenceRequest] = relationship(back_populates="signatures")
    user: Mapped[User] = relationship()


class AccessLog(Base):
    """LGPD: registro de acesso a dados sensíveis (motivo, anexo, relatórios)."""
    __tablename__ = "access_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(60))
    resource: Mapped[str] = mapped_column(String(120))
    ip: Mapped[str | None] = mapped_column(String(60), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    user: Mapped[User | None] = relationship()
