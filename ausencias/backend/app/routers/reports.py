"""Relatórios consolidados do RH (JSON, CSV, PDF) e painel de indicadores."""
import csv
import io
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..constants import POST_APPROVAL, STATUS_LABELS, TYPE_LABELS, Role, Status as S
from ..database import get_db
from ..models import AbsenceRequest, User
from ..security import client_ip, require_roles
from ..services.audit_service import log_access
from ..services.pdf_service import build_report_pdf
from ..utils import fmt_date, fmt_dt

router = APIRouter(prefix="/api", tags=["Relatórios e indicadores"])


def _filters(date_from: date | None, date_to: date | None, course_id: int | None,
             teacher_id: int | None, type: str | None, status: str | None):
    return dict(date_from=date_from, date_to=date_to, course_id=course_id, teacher_id=teacher_id, type=type, status=status)


def report_query(db: Session, f: dict) -> list[AbsenceRequest]:
    # RH só enxerga ausências aprovadas em diante (LGPD: mínimo necessário)
    q = select(AbsenceRequest).where(AbsenceRequest.status.in_(POST_APPROVAL))
    if f["date_from"]:
        q = q.where(AbsenceRequest.end_date >= f["date_from"])
    if f["date_to"]:
        q = q.where(AbsenceRequest.start_date <= f["date_to"])
    for col, key in ((AbsenceRequest.course_id, "course_id"), (AbsenceRequest.teacher_id, "teacher_id"),
                     (AbsenceRequest.type, "type"), (AbsenceRequest.status, "status")):
        if f[key]:
            q = q.where(col == f[key])
    return db.scalars(q.order_by(AbsenceRequest.start_date.desc())).all()


def to_rows(reqs):
    return [dict(protocol=r.protocol, teacher=r.teacher.name, course=r.course.name, type=TYPE_LABELS[r.type],
                 start_date=fmt_date(r.start_date), end_date=fmt_date(r.end_date), days=r.days,
                 status=STATUS_LABELS[r.status], returns=r.returns_count,
                 substitute=r.substitute.name if r.substitute else "",
                 sent_at=fmt_dt(r.sent_at), closed_at=fmt_dt(r.closed_at),
                 lead_days=round((r.closed_at - r.sent_at).total_seconds() / 86400, 1) if r.closed_at and r.sent_at else "") for r in reqs]


def totals(reqs):
    out = dict(count=len(reqs), days=sum(r.days for r in reqs), by_type={}, by_course={}, by_status={})
    for key, fn in (("by_type", lambda r: TYPE_LABELS[r.type]), ("by_course", lambda r: r.course.name),
                    ("by_status", lambda r: STATUS_LABELS[r.status])):
        acc = defaultdict(lambda: dict(count=0, days=0))
        for r in reqs:
            acc[fn(r)]["count"] += 1
            acc[fn(r)]["days"] += r.days
        out[key] = dict(acc)
    return out


def describe(f):
    parts = [f"{k}={v}" for k, v in f.items() if v]
    return ", ".join(parts) or "nenhum (todas as ausências aprovadas)"


@router.get("/reports/rh")
def report_json(date_from: date | None = None, date_to: date | None = None, course_id: int | None = None,
                teacher_id: int | None = None, type: str | None = None, status: str | None = None,
                u: User = Depends(require_roles(Role.RH)), db: Session = Depends(get_db)):
    reqs = report_query(db, _filters(date_from, date_to, course_id, teacher_id, type, status))
    return dict(rows=to_rows(reqs), totals=totals(reqs))


@router.get("/reports/rh.csv")
def report_csv(request: Request, date_from: date | None = None, date_to: date | None = None, course_id: int | None = None,
               teacher_id: int | None = None, type: str | None = None, status: str | None = None,
               u: User = Depends(require_roles(Role.RH)), db: Session = Depends(get_db)):
    f = _filters(date_from, date_to, course_id, teacher_id, type, status)
    rows = to_rows(report_query(db, f))
    log_access(db, u, "EXPORTOU_RELATORIO_CSV", describe(f)[:110], client_ip(request))
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Protocolo", "Docente", "Curso", "Tipo", "Início", "Fim", "Dias", "Status", "Devoluções", "Substituto", "Enviada em", "Encerrada em", "Tempo de tramitação (dias)"])
    for r in rows:
        w.writerow([r[k] for k in ("protocol", "teacher", "course", "type", "start_date", "end_date", "days", "status", "returns", "substitute", "sent_at", "closed_at", "lead_days")])
    # BOM para o Excel abrir com acentos corretos
    return Response(("\ufeff" + buf.getvalue()).encode("utf-8"), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="relatorio_ausencias.csv"'})


@router.get("/reports/rh.pdf")
def report_pdf(request: Request, date_from: date | None = None, date_to: date | None = None, course_id: int | None = None,
               teacher_id: int | None = None, type: str | None = None, status: str | None = None,
               u: User = Depends(require_roles(Role.RH)), db: Session = Depends(get_db)):
    f = _filters(date_from, date_to, course_id, teacher_id, type, status)
    reqs = report_query(db, f)
    log_access(db, u, "EXPORTOU_RELATORIO_PDF", describe(f)[:110], client_ip(request))
    pdf = build_report_pdf(to_rows(reqs), totals(reqs), describe(f), u.name)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": 'inline; filename="relatorio_ausencias.pdf"'})


@router.get("/reports/teachers")
def report_teachers(u: User = Depends(require_roles(Role.RH)), db: Session = Depends(get_db)):
    """Lista de docentes e cursos para os filtros (apenas id e nome)."""
    from ..models import Course
    teachers = db.scalars(select(User).where(User.role.in_(Role.CAN_REQUEST)).order_by(User.name)).all()
    return dict(teachers=[dict(id=t.id, name=t.name) for t in teachers],
                courses=[dict(id=c.id, name=c.name) for c in db.scalars(select(Course).order_by(Course.name))])


# ---------- indicadores (sustentam a hipótese do artigo) ----------
@router.get("/dashboard")
def dashboard(u: User = Depends(require_roles(Role.RH, Role.COORDENADOR)), db: Session = Depends(get_db)):
    q = select(AbsenceRequest).where(AbsenceRequest.status != S.RASCUNHO)
    if u.role == Role.COORDENADOR:
        q = q.where(AbsenceRequest.course_id == u.course_id)
    reqs = db.scalars(q).all()           # apenas agregados são devolvidos (sem dados pessoais)

    closed = [r for r in reqs if r.status == S.ENCERRADA and r.sent_at and r.closed_at]
    avg_total = sum((r.closed_at - r.sent_at).total_seconds() for r in closed) / len(closed) / 3600 if closed else None

    # tempo até a decisão da coordenação (1ª entrada em análise -> 1ª decisão seguinte)
    decisions = []
    for r in reqs:
        start = next((e.created_at for e in r.events if e.to_status == S.EM_ANALISE), None)
        end = next((e.created_at for e in r.events if start and e.created_at >= start and e.to_status in (S.APROVADA, S.DEVOLVIDA, S.RECUSADA)), None)
        if start and end:
            decisions.append((end - start).total_seconds() / 3600)

    count = lambda fn: {k: v for k, v in sorted(_counter(reqs, fn).items(), key=lambda x: -x[1])}
    with_return = sum(1 for r in reqs if r.returns_count > 0)
    return dict(
        total=len(reqs),
        avg_lead_hours=round(avg_total, 1) if avg_total is not None else None,
        avg_coord_decision_hours=round(sum(decisions) / len(decisions), 1) if decisions else None,
        returns_total=sum(r.returns_count for r in reqs),
        requests_with_return=with_return,
        rework_rate=round(100 * with_return / len(reqs), 1) if reqs else 0,
        closed=len(closed),
        by_status=count(lambda r: STATUS_LABELS[r.status]),
        by_type=count(lambda r: TYPE_LABELS[r.type]),
        by_course=count(lambda r: r.course.name),
    )


def _counter(items, fn):
    acc = defaultdict(int)
    for i in items:
        acc[fn(i)] += 1
    return acc
