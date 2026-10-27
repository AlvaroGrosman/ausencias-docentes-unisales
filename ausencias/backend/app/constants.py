"""Perfis, estados e rótulos em português usados em todo o sistema."""


class Role:
    DOCENTE = "DOCENTE"
    COORDENADOR = "COORDENADOR"
    SUBSTITUTO = "SUBSTITUTO"
    SALA = "SALA_PROFESSORES"
    RH = "RH"
    ADMIN = "ADMIN"
    ALL = [DOCENTE, COORDENADOR, SUBSTITUTO, SALA, RH, ADMIN]
    CAN_REQUEST = (DOCENTE, SUBSTITUTO)          # quem pode abrir solicitação
    CAN_SUBSTITUTE = (DOCENTE, SUBSTITUTO)       # quem pode ser indicado como substituto


ROLE_LABELS = {
    Role.DOCENTE: "Docente",
    Role.COORDENADOR: "Coordenador",
    Role.SUBSTITUTO: "Docente substituto",
    Role.SALA: "Sala dos Professores",
    Role.RH: "RH",
    Role.ADMIN: "Administrador",
}


class Status:
    RASCUNHO = "RASCUNHO"
    ENVIADA = "ENVIADA"
    EM_ANALISE = "EM_ANALISE_COORDENACAO"
    DEVOLVIDA = "DEVOLVIDA"
    APROVADA = "APROVADA"
    AGUARDANDO_SUBSTITUTO = "AGUARDANDO_SUBSTITUTO"
    REGISTRADA = "REGISTRADA_SALA_PROFESSORES"
    ENCERRADA = "ENCERRADA_RH"
    RECUSADA = "RECUSADA"
    CANCELADA = "CANCELADA"


STATUS_LABELS = {
    Status.RASCUNHO: "Rascunho",
    Status.ENVIADA: "Enviada",
    Status.EM_ANALISE: "Em análise (Coordenação)",
    Status.DEVOLVIDA: "Devolvida ao docente",
    Status.APROVADA: "Aprovada",
    Status.AGUARDANDO_SUBSTITUTO: "Aguardando substituto",
    Status.REGISTRADA: "Registrada (Sala dos Professores)",
    Status.ENCERRADA: "Encerrada (RH)",
    Status.RECUSADA: "Recusada",
    Status.CANCELADA: "Cancelada",
}

TYPE_LABELS = {"PROGRAMADA": "Programada", "NAO_PROGRAMADA": "Não programada"}

# Estados finais (nenhuma transição saindo deles)
TERMINAL = {Status.ENCERRADA, Status.RECUSADA, Status.CANCELADA}

# LGPD: Sala dos Professores e RH só enxergam ausências já aprovadas
POST_APPROVAL = {Status.APROVADA, Status.AGUARDANDO_SUBSTITUTO, Status.REGISTRADA, Status.ENCERRADA}
