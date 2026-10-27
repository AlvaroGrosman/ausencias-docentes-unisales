"""Solicitações de ausência: CRUD do rascunho, caixa de entrada, detalhe, ações do workflow, PDF, anexo."""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from ..constants import POST_APPROVAL, ROLE_LABELS, STATUS_LABELS, TYPE_LABELS, Role, Status as S
from ..database import BASE_DIR, get_db
from ..models import AbsenceRequest, User
from ..schemas import ActionIn, RequestIn
from ..security import client_ip, get_current_user
from ..services.audit_service import log_access, log_event
from ..services.pdf_service import build_request_pdf
from ..services.signature_service import is_valid
from ..utils import now
from ..workflow import EVENT_LABELS, allowed_actions, apply_action

router = APIRouter(prefix="/api", tags=["Solicitações"])
UPLOADS = BASE_DIR / "uploads"
EDITABLE = (S.RASCUNHO, S.DEVOLVIDA)


# ---------- visibilidade (LGPD: o mínimo necessário por perfil) ----------
def can_view(req: AbsenceRequest, u: User) -> bool:
    if u.id == req.teacher_id or u.id == req.substitute_id:
        return True
    if u.role == Role.COORDENADOR:
        return u.course_id == req.course_id and req.status != S.RASCUNHO
    if u.role in (Role.SALA, Role.RH):
        return req.status in POST_APPROVAL
    return False


def can_see_reason(req: AbsenceRequest, u: User) -> bool:
    """Motivo/observações/anexo: docente autor, coordenador do curso e RH. Sala e substituto não."""
    return u.id == req.teacher_id or u.role == Role.RH or (u.role == Role.COORDENADOR and u.course_id == req.course_id)


def _scope(u: User):
    c = [AbsenceRequest.teacher_id == u.id, AbsenceRequest.substitute_id == u.id]
    if u.role == Role.COORDENADOR:
        c.append(and_(AbsenceRequest.course_id == u.course_id, AbsenceRequest.status != S.RASCUNHO))
    if u.role in (Role.SALA, Role.RH):
        c.append(AbsenceRequest.status.in_(POST_APPROVAL))
    return or_(*c)


def _inbox(u: User):
    """Pendências: o que depende de uma ação deste usuário agora."""
    c = [and_(AbsenceRequest.teacher_id == u.id, AbsenceRequest.status.in_(EDITABLE)),
         and_(AbsenceRequest.substitute_id == u.id, AbsenceRequest.status == S.AGUARDANDO_SUBSTITUTO,
              AbsenceRequest.substitute_status == "PENDENTE")]
    if u.role == Role.COORDENADOR:
        c.append(and_(AbsenceRequest.course_id == u.course_id, AbsenceRequest.status == S.EM_ANALISE))
    if u.role == Role.SALA:
        c.append(or_(AbsenceRequest.status == S.APROVADA,
                     and_(AbsenceRequest.status == S.AGUARDANDO_SUBSTITUTO, AbsenceRequest.substitute_status == "ACEITA")))
    if u.role == Role.RH:
        c.append(AbsenceRequest.status == S.REGISTRADA)
    return or_(*c)


def _person(u):
    return {"id": u.id, "name": u.name} if u else None


def serialize(req: AbsenceRequest, u: User, detail=False) -> dict:
    see = can_see_reason(req, u)
    d = dict(id=req.id, protocol=req.protocol, type=req.type, type_label=TYPE_LABELS[req.type],
             status=req.status, status_label=STATUS_LABELS[req.status], teacher=_person(req.teacher),
             course=dict(id=req.course.id, name=req.course.name), start_date=req.start_date.isoformat(),
             end_date=req.end_date.isoformat(), days=req.days, subjects=req.subjects,
             reason=req.reason if see else None, notes=req.notes if see else None, reason_restricted=not see,
             has_attachment=bool(req.attachment_path) and see, attachment_name=req.attachment_name if see else None,
             suggested_substitute=_person(req.suggested_substitute), substitute=_person(req.substitute),
             substitute_status=req.substitute_status, returns_count=req.returns_count,
             created_at=req.created_at, sent_at=req.sent_at, closed_at=req.closed_at, updated_at=req.updated_at)
    if detail:
        d["can_edit"] = u.id == req.teacher_id and req.status in EDITABLE
        d["allowed_actions"] = allowed_actions(req, u)
        d["events"] = [dict(id=e.id, user=e.user.name if e.user else "Sistema",
                            role_label=ROLE_LABELS[e.user.role] if e.user else None, action=e.action,
                            action_label=EVENT_LABELS.get(e.action, e.action), from_status=e.from_status,
                            to_status=e.to_status, note=e.note, created_at=e.created_at) for e in req.events]
        d["signatures"] = [dict(id=s.id, user=s.user.name, role_label=ROLE_LABELS.get(s.role, s.role), signed_at=s.signed_at,
                                ip=s.ip, hash=s.content_hash, algorithm=s.algorithm, valid=is_valid(req, s)) for s in req.signatures]
    return d


def load(db: Session, rid: int, u: User) -> AbsenceRequest:
    req = db.get(AbsenceRequest, rid)
    if not req or not can_view(req, u):   # 404 também para quem não pode ver (não revela existência)
        raise HTTPException(404, "Solicitação não encontrada.")
    return req


def _check_substitute(db, sid, teacher_id):
    if sid is None:
        return
    s = db.get(User, sid)
    if not s or not s.active or s.role not in Role.CAN_SUBSTITUTE or s.id == teacher_id:
        raise HTTPException(422, "Substituto sugerido inválido.")


# ---------- listagem / CRUD ----------
@router.get("/requests")
def list_requests(inbox: bool = False, status: str | None = None, type: str | None = None,
                  u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if u.role == Role.ADMIN:
        raise HTTPException(403, "O administrador não acessa solicitações (princípio do mínimo necessário).")
    q = select(AbsenceRequest).where(_scope(u))
    if inbox:
        q = q.where(_inbox(u))
    if status:
        q = q.where(AbsenceRequest.status == status)
    if type:
        q = q.where(AbsenceRequest.type == type)
    rows = db.scalars(q.order_by(AbsenceRequest.updated_at.desc())).all()
    return [serialize(r, u) for r in rows]


@router.get("/requests/inbox-count")
def inbox_count(u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if u.role == Role.ADMIN:
        return {"count": 0}
    return {"count": len(db.scalars(select(AbsenceRequest.id).where(_scope(u), _inbox(u))).all())}


@router.post("/requests", status_code=201)
def create_request(data: RequestIn, request: Request, u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if u.role not in Role.CAN_REQUEST or not u.course_id:
        raise HTTPException(403, "Apenas docentes vinculados a um curso podem abrir solicitações.")
    _check_substitute(db, data.suggested_substitute_id, u.id)
    req = AbsenceRequest(teacher_id=u.id, course_id=u.course_id, status=S.RASCUNHO, **data.model_dump())
    db.add(req)
    db.flush()
    log_event(db, req, u, "create", None, S.RASCUNHO)
    db.commit()
    return serialize(req, u, detail=True)


@router.put("/requests/{rid}")
def update_request(rid: int, data: RequestIn, u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    req = load(db, rid, u)
    if u.id != req.teacher_id or req.status not in EDITABLE:
        raise HTTPException(409, "A solicitação só pode ser editada pelo docente em rascunho ou quando devolvida.")
    _check_substitute(db, data.suggested_substitute_id, u.id)
    for k, v in data.model_dump().items():
        setattr(req, k, v)
    req.updated_at = now()
    db.commit()
    return serialize(req, u, detail=True)


@router.get("/requests/{rid}")
def get_request(rid: int, request: Request, u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    req = load(db, rid, u)
    if can_see_reason(req, u) and u.id != req.teacher_id:   # LGPD: acesso de terceiros a dado sensível
        log_access(db, u, "VISUALIZOU_DADOS_SENSIVEIS", req.protocol, client_ip(request))
    return serialize(req, u, detail=True)


@router.post("/requests/{rid}/actions/{action}")
def do_action(rid: int, action: str, data: ActionIn, request: Request,
              u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    req = load(db, rid, u)
    apply_action(db, req, u, action, data.note, data.substitute_id, client_ip(request))
    return serialize(req, u, detail=True)


# ---------- PDF e anexo ----------
@router.get("/requests/{rid}/pdf")
def request_pdf(rid: int, request: Request, u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    req = load(db, rid, u)
    if can_see_reason(req, u) and u.id != req.teacher_id:
        log_access(db, u, "BAIXOU_PDF_COM_DADOS_SENSIVEIS", req.protocol, client_ip(request))
    pdf = build_request_pdf(req, can_see_reason(req, u))
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{req.protocol}.pdf"'})


@router.post("/requests/{rid}/attachment")
async def upload_attachment(rid: int, file: UploadFile = File(...), u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    req = load(db, rid, u)
    if u.id != req.teacher_id or req.status not in EDITABLE:
        raise HTTPException(409, "Anexo só pode ser alterado pelo docente em rascunho ou devolvida.")
    ext = Path(file.filename or "").suffix.lower()
    if ext not in (".pdf", ".png", ".jpg", ".jpeg"):
        raise HTTPException(422, "Formato não permitido. Envie PDF, PNG ou JPG.")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(422, "Arquivo maior que 5 MB.")
    UPLOADS.mkdir(exist_ok=True)
    path = UPLOADS / f"{req.id}_{uuid.uuid4().hex}{ext}"
    path.write_bytes(content)
    req.attachment_name, req.attachment_path, req.updated_at = Path(file.filename).name[:190], str(path), now()
    db.commit()
    return serialize(req, u, detail=True)


@router.get("/requests/{rid}/attachment")
def get_attachment(rid: int, request: Request, u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    req = load(db, rid, u)
    if not can_see_reason(req, u) or not req.attachment_path or not Path(req.attachment_path).exists():
        raise HTTPException(404, "Anexo não disponível.")
    if u.id != req.teacher_id:
        log_access(db, u, "BAIXOU_ANEXO", req.protocol, client_ip(request))
    return FileResponse(req.attachment_path, filename=req.attachment_name)


# ---------- apoio ao formulário ----------
@router.get("/substitute-candidates")
def substitute_candidates(u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = select(User).where(User.active.is_(True), User.role.in_(Role.CAN_SUBSTITUTE), User.id != u.id).order_by(User.name)
    return [dict(id=s.id, name=s.name, course_name=s.course_name) for s in db.scalars(q)]
