"""
Camada de ASSINATURA ELETRÔNICA (SIMULADA), isolada do resto do sistema.

O restante da aplicação só conhece `get_signature_provider()` e a interface
`SignatureProvider`. Para usar Clicksign/DocuSign (artigo, seção 3), basta criar
uma classe que implemente `sign()` e `verify()` chamando a API do provedor e
trocar o retorno de `get_signature_provider()` — workflow, PDF e telas não mudam.
"""
import hashlib
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from ..models import AbsenceRequest, Signature, User


@dataclass
class SignatureResult:
    content_hash: str
    algorithm: str
    signed_at: datetime
    ip: str


def canonical_content(req: AbsenceRequest) -> dict:
    """Conteúdo da solicitação que é 'selado' pelo hash (o substituto indicado pela
    coordenação fica de fora de propósito: ele é definido depois da assinatura do docente)."""
    return {
        "protocolo": req.protocol,
        "docente_id": req.teacher_id,
        "curso_id": req.course_id,
        "tipo": req.type,
        "inicio": req.start_date.isoformat(),
        "fim": req.end_date.isoformat(),
        "disciplinas": req.subjects,
        "motivo": req.reason,
        "observacoes": req.notes or "",
        "substituto_sugerido_id": req.suggested_substitute_id,
        "anexo": req.attachment_name or "",
    }


def compute_hash(content: dict) -> str:
    raw = json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class SignatureProvider(ABC):
    """Interface que um provedor real (Clicksign, DocuSign...) precisaria implementar."""

    @abstractmethod
    def sign(self, req: AbsenceRequest, user: User, ip: str, at: datetime) -> SignatureResult: ...

    @abstractmethod
    def verify(self, req: AbsenceRequest, signature: Signature) -> bool: ...


class SimulatedProvider(SignatureProvider):
    """Registra usuário, data/hora, IP e SHA-256 do conteúdo no momento da assinatura."""
    algorithm = "SHA-256 (simulada)"

    def sign(self, req, user, ip, at):
        return SignatureResult(compute_hash(canonical_content(req)), self.algorithm, at, ip)

    def verify(self, req, signature):
        # válida = o conteúdo atual ainda gera o mesmo hash registrado na assinatura
        return compute_hash(canonical_content(req)) == signature.content_hash


def get_signature_provider() -> SignatureProvider:
    # Ponto único de troca: os.getenv("SIGNATURE_PROVIDER") == "clicksign" -> ClicksignProvider()
    return SimulatedProvider()


def sign_request(db: Session, req: AbsenceRequest, user: User, ip: str, at: datetime) -> Signature:
    res = get_signature_provider().sign(req, user, ip, at)
    sig = Signature(request_id=req.id, user_id=user.id, role=user.role, signed_at=res.signed_at,
                    ip=res.ip, content_hash=res.content_hash, algorithm=res.algorithm)
    db.add(sig)
    return sig


def is_valid(req: AbsenceRequest, sig: Signature) -> bool:
    return get_signature_provider().verify(req, sig)
