"""
MÁQUINA DE ESTADOS da solicitação (fluxo TO-BE do artigo).

RASCUNHO -> ENVIADA -> EM_ANALISE -> (DEVOLVIDA | APROVADA | RECUSADA)
APROVADA -> AGUARDANDO_SUBSTITUTO (se houver substituto) -> REGISTRADA -> ENCERRADA
CANCELADA: o docente pode cancelar antes do registro pela Sala.

Toda regra vive aqui: quem pode executar cada ação e de qual estado. Os routers só
chamam `apply_action`; o frontend apenas exibe `allowed_actions`.
Cada transição grava evento de auditoria, notificação e (quando aplicável) assinatura.
"""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .constants import Role, Status as S, TERMINAL
from .models import AbsenceRequest, User
from .services.audit_service import log_event
from .services.notification_service import notify, users_with_role
from .services.signature_service import sign_request
from .utils import now

# label do botão, exige observação?, exige escolha de substituto?
ACTIONS = {
    "submit":  dict(label="Assinar e enviar", note=False),
    "cancel":  dict(label="Cancelar solicitação", note=False),
    "approve": dict(label="Aprovar e assinar", note=False, substitute=True),
    "return":  dict(label="Devolver ao docente", note=True),
    "reject":  dict(label="Recusar", note=True),
    "accept_substitute":  dict(label="Aceitar substituição", note=False),
    "decline_substitute": dict(label="Recusar substituição", note=True),
    "register": dict(label="Confirmar registro", note=False),
    "close":   dict(label="Encerrar (RH)", note=False),
}


def check(req: AbsenceRequest, user: User, action: str) -> tuple[int, str] | None:
    """Retorna None se permitido; senão (http_status, mensagem)."""
    if action not in ACTIONS:
        return 404, "Ação desconhecida."
    st = req.status
    if action in ("submit", "cancel"):
        if user.id != req.teacher_id:
            return 403, "Somente o docente autor pode executar esta ação."
        ok = {S.RASCUNHO, S.DEVOLVIDA} if action == "submit" else (
            {S.RASCUNHO, S.EM_ANALISE, S.DEVOLVIDA, S.APROVADA, S.AGUARDANDO_SUBSTITUTO})
        if st not in ok:
            return 409, f"Transição inválida: não é possível '{ACTIONS[action]['label']}' no status atual."
    elif action in ("approve", "return", "reject"):
        if user.role != Role.COORDENADOR or user.course_id != req.course_id:
            return 403, "Somente o coordenador do curso pode analisar esta solicitação."
        if st != S.EM_ANALISE:
            return 409, "Transição inválida: a solicitação não está em análise pela Coordenação."
    elif action in ("accept_substitute", "decline_substitute"):
        if user.id != req.substitute_id:
            return 403, "Somente o substituto indicado pode responder."
        if st != S.AGUARDANDO_SUBSTITUTO or req.substitute_status != "PENDENTE":
            return 409, "Transição inválida: não há substituição pendente de resposta."
    elif action == "register":
        if user.role != Role.SALA:
            return 403, "Somente a Sala dos Professores pode registrar."
        if not (st == S.APROVADA or (st == S.AGUARDANDO_SUBSTITUTO and req.substitute_status == "ACEITA")):
            return 409, "Transição inválida: a ausência ainda não está pronta para registro."
    elif action == "close":
        if user.role != Role.RH:
            return 403, "Somente o RH pode encerrar."
        if st != S.REGISTRADA:
            return 409, "Transição inválida: a ausência ainda não foi registrada pela Sala dos Professores."
    return None


def allowed_actions(req: AbsenceRequest, user: User) -> list[dict]:
    return [dict(action=a, label=m["label"], needs_note=m["note"], needs_substitute=m.get("substitute", False))
            for a, m in ACTIONS.items() if check(req, user, a) is None]


def _move(db, req, user, action, to, note, at, ip, sign=False):
    prev = req.status
    req.status, req.updated_at = to, at
    db.flush()
    log_event(db, req, user, action, prev, to, note, at)
    if sign and user:
        sign_request(db, req, user, ip or "desconhecido", at)


def apply_action(db: Session, req: AbsenceRequest, user: User, action: str, note: str | None = None,
                 substitute_id: int | None = None, ip: str | None = None, at=None) -> AbsenceRequest:
    at = at or now()
    note = (note or "").strip() or None
    err = check(req, user, action)
    if err:
        raise HTTPException(*err)
    if ACTIONS[action]["note"] and not note:
        raise HTTPException(422, "Informe a justificativa/observação para esta ação.")
    teacher = req.teacher_id

    if action == "submit":
        if not req.subjects.strip() or not req.reason.strip():
            raise HTTPException(422, "Preencha disciplinas/turmas e motivo antes de enviar.")
        _move(db, req, user, "submit", S.ENVIADA, note, at, ip, sign=True)
        req.sent_at = req.sent_at or at
        _move(db, req, None, "auto_analysis", S.EM_ANALISE, "Encaminhada automaticamente à Coordenação", at, ip)
        notify(db, users_with_role(db, Role.COORDENADOR, req.course_id), req,
               f"nova solicitação de {req.teacher.name} aguardando análise", at)

    elif action == "return":
        req.returns_count += 1
        _move(db, req, user, "return", S.DEVOLVIDA, note, at, ip)
        notify(db, [teacher], req, "devolvida pela Coordenação — ajuste e reenvie", at)

    elif action == "reject":
        req.closed_at = at
        _move(db, req, user, "reject", S.RECUSADA, note, at, ip)
        notify(db, [teacher], req, "solicitação recusada pela Coordenação", at)

    elif action == "approve":
        sub = None
        if substitute_id:
            sub = db.get(User, substitute_id)
            if not sub or not sub.active or sub.role not in Role.CAN_SUBSTITUTE or sub.id == teacher:
                raise HTTPException(422, "Substituto inválido.")
        _move(db, req, user, "approve", S.APROVADA, note, at, ip, sign=True)
        if sub:
            req.substitute_id, req.substitute_status = sub.id, "PENDENTE"
            _move(db, req, None, "auto_substitute", S.AGUARDANDO_SUBSTITUTO,
                  f"Substituto indicado: {sub.name}", at, ip)
            notify(db, [sub.id], req, f"você foi indicado(a) como substituto(a) de {req.teacher.name}", at)
            notify(db, [teacher], req, f"aprovada; aguardando aceite do substituto {sub.name}", at)
        else:
            notify(db, users_with_role(db, Role.SALA), req, "ausência aprovada aguardando registro", at)
            notify(db, [teacher], req, "aprovada pela Coordenação", at)

    elif action == "accept_substitute":
        req.substitute_status = "ACEITA"
        log_event(db, req, user, "accept_substitute", S.AGUARDANDO_SUBSTITUTO, S.AGUARDANDO_SUBSTITUTO, note, at)
        req.updated_at = at
        sign_request(db, req, user, ip or "desconhecido", at)
        notify(db, users_with_role(db, Role.SALA), req, "substituição aceita — ausência pronta para registro", at)
        notify(db, [teacher], req, f"{user.name} aceitou a substituição", at)

    elif action == "decline_substitute":
        declined = user.name
        req.substitute_id = req.substitute_status = None
        _move(db, req, user, "decline_substitute", S.EM_ANALISE, f"{declined} recusou: {note}", at, ip)
        notify(db, users_with_role(db, Role.COORDENADOR, req.course_id), req,
               f"{declined} recusou a substituição — indique outro substituto", at)
        notify(db, [teacher], req, "substituto recusou; Coordenação indicará outro", at)

    elif action == "register":
        _move(db, req, user, "register", S.REGISTRADA, note, at, ip, sign=True)
        notify(db, users_with_role(db, Role.RH), req, "ausência registrada — pendente de encerramento", at)
        notify(db, [teacher], req, "ausência registrada pela Sala dos Professores", at)

    elif action == "close":
        req.closed_at = at
        _move(db, req, user, "close", S.ENCERRADA, note, at, ip, sign=True)
        notify(db, [teacher], req, "processo encerrado pelo RH", at)

    elif action == "cancel":
        was_sent = req.status != S.RASCUNHO
        req.closed_at = at
        _move(db, req, user, "cancel", S.CANCELADA, note, at, ip)
        if was_sent:
            notify(db, users_with_role(db, Role.COORDENADOR, req.course_id), req, "solicitação cancelada pelo docente", at)

    db.commit()
    return req


EVENT_LABELS = {
    "create": "Rascunho criado", "submit": "Assinada e enviada", "auto_analysis": "Encaminhada à Coordenação",
    "return": "Devolvida ao docente", "reject": "Recusada", "approve": "Aprovada e assinada",
    "auto_substitute": "Substituto indicado", "accept_substitute": "Substituição aceita",
    "decline_substitute": "Substituição recusada", "register": "Registrada pela Sala dos Professores",
    "close": "Encerrada pelo RH", "cancel": "Cancelada",
}
