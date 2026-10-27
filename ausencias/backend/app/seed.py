"""
Popula o banco com dados de demonstração (ATENÇÃO: apaga e recria todas as tabelas).
Uso (dentro de backend/):  python -m app.seed
Os históricos são gerados executando a própria máquina de estados (workflow.apply_action),
então eventos, notificações e assinaturas ficam coerentes com as regras reais.
"""
from datetime import date, timedelta

from .constants import Role, Status as S
from .database import Base, SessionLocal, engine
from .models import AbsenceRequest, Course, Notification, User
from .security import hash_password
from .services.audit_service import log_event
from .utils import now
from .workflow import apply_action

PASSWORD = "demo123"

USERS = [  # chave, nome, e-mail, perfil, curso
    ("admin", "Administrador do Sistema", "admin@demo.br", Role.ADMIN, None),
    ("t1", "Prof. Carlos Silva", "docente@demo.br", Role.DOCENTE, "SI"),
    ("t2", "Profa. Marina Souza", "docente2@demo.br", Role.DOCENTE, "SI"),
    ("t3", "Prof. Rafael Lima", "docente3@demo.br", Role.DOCENTE, "ADM"),
    ("c1", "Profa. Helena Costa (Coord. SI)", "coord@demo.br", Role.COORDENADOR, "SI"),
    ("c2", "Prof. Jorge Alves (Coord. ADM)", "coord2@demo.br", Role.COORDENADOR, "ADM"),
    ("sub", "Prof. Paulo Mendes", "substituto@demo.br", Role.SUBSTITUTO, "SI"),
    ("sala", "Sala dos Professores", "sala@demo.br", Role.SALA, None),
    ("rh", "Setor de RH", "rh@demo.br", Role.RH, None),
]
COURSES = {"SI": "Sistemas de Informação", "ADM": "Administração"}

# (docente, tipo, início em dias relativos a hoje, duração, disciplinas, motivo, dias atrás da criação, passos)
# passo = (ator, ação, observação, substituto, horas após o passo anterior) ; ação "edit" altera o motivo
SUBMIT = ("{t}", "submit", None, None, 1)
SCENARIOS = [
    ("t1", "PROGRAMADA", 12, 1, "Banco de Dados II — turma 7SI", "Apresentação de artigo em congresso nacional.", 1, []),
    ("t3", "NAO_PROGRAMADA", 0, 1, "Gestão de Pessoas — turma 3ADM", "Consulta médica de urgência.", 0, []),
    ("t1", "PROGRAMADA", 9, 2, "Engenharia de Software — turma 5SI", "Participação em banca de doutorado em outra instituição.", 1, [("t1", "submit", None, None, 2)]),
    ("t3", "PROGRAMADA", 15, 1, "Marketing — turma 4ADM", "Visita técnica com outra turma.", 2, [("t3", "submit", None, None, 3)]),
    ("t2", "PROGRAMADA", 8, 3, "Redes de Computadores — turma 6SI", "Curso de capacitação.", 3,
     [("t2", "submit", None, None, 2), ("c1", "return", "Informe o comprovante da capacitação e as turmas impactadas.", None, 20)]),
    ("t1", "PROGRAMADA", 5, 1, "Programação Web — turma 3SI", "Evento acadêmico regional.", 4,
     [("t1", "submit", None, None, 2), ("c1", "approve", "De acordo.", None, 18)]),
    ("t2", "PROGRAMADA", 4, 2, "Estruturas de Dados — turma 2SI", "Congresso de educação.", 5,
     [("t2", "submit", None, None, 2), ("c1", "approve", "Indico o prof. Paulo para cobrir as aulas.", "sub", 15)]),
    ("t1", "PROGRAMADA", 3, 1, "Algoritmos — turma 1SI", "Reunião de projeto de pesquisa.", 6,
     [("t1", "submit", None, None, 1), ("c1", "approve", None, "sub", 10), ("sub", "accept_substitute", "Posso cobrir.", None, 6)]),
    ("t2", "PROGRAMADA", -2, 2, "Sistemas Operacionais — turma 4SI", "Treinamento obrigatório da instituição parceira.", 9,
     [("t2", "submit", None, None, 1), ("c1", "approve", None, "sub", 20), ("sub", "accept_substitute", None, None, 5),
      ("sala", "register", "Registrado no mural e no diário.", None, 12)]),
    ("t3", "NAO_PROGRAMADA", -3, 1, "Contabilidade — turma 5ADM", "Problema de saúde na família.", 6,
     [("t3", "submit", None, None, 2), ("c2", "approve", None, None, 8), ("sala", "register", None, None, 6)]),
    ("t1", "PROGRAMADA", -14, 2, "Análise de Sistemas — turma 6SI", "Participação em evento de tecnologia.", 20,
     [("t1", "submit", None, None, 1), ("c1", "return", "Falta indicar o período correto das aulas.", None, 30),
      ("t1", "edit", " Período corrigido conforme calendário.", None, 5), ("t1", "submit", None, None, 1),
      ("c1", "approve", None, "sub", 12), ("sub", "accept_substitute", None, None, 4),
      ("sala", "register", None, None, 10), ("rh", "close", "Conferido e arquivado.", None, 30)]),
    ("t2", "NAO_PROGRAMADA", -20, 1, "Banco de Dados I — turma 3SI", "Imprevisto de transporte.", 19,
     [("t2", "submit", None, None, 26), ("c1", "approve", None, None, 6), ("sala", "register", None, None, 4), ("rh", "close", None, None, 22)]),
    ("t3", "PROGRAMADA", -25, 3, "Administração Financeira — turma 7ADM", "Missão técnica a empresa parceira.", 30,
     [("t3", "submit", None, None, 3), ("c2", "approve", None, None, 14), ("sala", "register", None, None, 8), ("rh", "close", None, None, 26)]),
    ("t1", "PROGRAMADA", -7, 1, "Gestão de Projetos — turma 8SI", "Compromisso pessoal.", 10,
     [("t1", "submit", None, None, 2), ("c1", "reject", "Período de avaliações: não é possível ausentar-se nesta data.", None, 24)]),
    ("t2", "PROGRAMADA", 6, 1, "Inteligência Artificial — turma 7SI", "Curso externo.", 3,
     [("t2", "submit", None, None, 2), ("t2", "cancel", "Evento adiado.", None, 30)]),
]


def run():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    courses = {k: Course(name=v) for k, v in COURSES.items()}
    db.add_all(courses.values())
    db.flush()
    pw = hash_password(PASSWORD)
    users = {}
    for key, name, email, role, c in USERS:
        users[key] = User(name=name, email=email, password_hash=pw, role=role, course_id=courses[c].id if c else None)
        db.add(users[key])
    db.flush()

    today = date.today()
    for teacher, typ, start_off, dur, subjects, reason, created_ago, steps in SCENARIOS:
        t = users[teacher]
        at = now() - timedelta(days=created_ago, hours=1)
        req = AbsenceRequest(teacher_id=t.id, course_id=t.course_id, type=typ, start_date=today + timedelta(days=start_off),
                             end_date=today + timedelta(days=start_off + dur - 1), subjects=subjects, reason=reason,
                             status=S.RASCUNHO, created_at=at, updated_at=at)
        db.add(req)
        db.flush()
        log_event(db, req, t, "create", None, S.RASCUNHO, None, at)
        for actor, action, note, sub, hours in steps:
            at += timedelta(hours=hours)
            if at > now():
                at = now()
            if action == "edit":
                req.reason += note
                req.updated_at = at
                continue
            apply_action(db, req, users[actor], action, note, users[sub].id if sub else None, "10.0.0.%d" % (10 + list(users).index(actor)), at)
        db.commit()

    # notificações antigas já "lidas"; só as dos últimos 2 dias ficam não lidas
    cutoff = now() - timedelta(days=2)
    for n in db.query(Notification).all():
        n.read = n.created_at < cutoff
    db.commit()
    print(f"Seed concluído: {len(users)} usuários, {len(SCENARIOS)} solicitações. Senha de todos: {PASSWORD}")
    for key, name, email, role, _ in USERS:
        print(f"  {email:24s} {role}")
    db.close()


if __name__ == "__main__":
    run()
