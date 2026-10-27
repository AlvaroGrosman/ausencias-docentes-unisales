"""
Teste de ponta a ponta do fluxo:  python test_flow.py
Usa um banco temporário (não toca no ausencias.db). Sai com código 1 se algo falhar.
"""
import os
import sys
import tempfile
from datetime import date, timedelta

tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/teste.db"

from fastapi.testclient import TestClient  # noqa: E402

from app import seed  # noqa: E402
from app.main import app  # noqa: E402

seed.run()
c = TestClient(app)
PW = "demo123"


def login(email):
    r = c.post("/api/auth/login", json={"email": email, "password": PW})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def step(msg):
    print(f"  ✔ {msg}")


def act(h, rid, action, expect=200, **body):
    r = c.post(f"/api/requests/{rid}/actions/{action}", json=body, headers=h)
    assert r.status_code == expect, f"{action}: esperado {expect}, veio {r.status_code} {r.text}"
    return r.json()


H = {k: login(f"{v}@demo.br") for k, v in dict(doc="docente", doc2="docente2", doc3="docente3", coord="coord", coord2="coord2",
                                                  sub="substituto", sala="sala", rh="rh", admin="admin").items()}
step("login de todos os perfis")
assert c.post("/api/auth/login", json={"email": "docente@demo.br", "password": "errada"}).status_code == 401
assert c.get("/api/requests").status_code == 401
step("senha errada e acesso sem token recusados")

subs = c.get("/api/substitute-candidates", headers=H["doc"]).json()
sub_id = next(s["id"] for s in subs if s["name"] == "Prof. Paulo Mendes")

# --- validações
bad = c.post("/api/requests", headers=H["doc"], json=dict(type="PROGRAMADA", start_date=str(date.today() - timedelta(days=3)),
             end_date=str(date.today()), subjects="Cálculo", reason="Evento"))
assert bad.status_code == 422 and "programada" in bad.json()["detail"].lower(), bad.text
step("validação em português (programada no passado)")

# --- docente cria e envia
start = date.today() + timedelta(days=7)
r = c.post("/api/requests", headers=H["doc"], json=dict(type="PROGRAMADA", start_date=str(start), end_date=str(start + timedelta(days=1)),
           subjects="Banco de Dados — 5SI", reason="Congresso", notes="Levarei material", suggested_substitute_id=sub_id))
assert r.status_code == 201, r.text
rid = r.json()["id"]
assert r.json()["status"] == "RASCUNHO"
up = c.post(f"/api/requests/{rid}/attachment", headers=H["doc"], files={"file": ("convite.pdf", b"%PDF-1.4 teste", "application/pdf")})
assert up.status_code == 200 and up.json()["has_attachment"]
step("docente cria rascunho com anexo")

# --- privacidade e permissões
assert c.get(f"/api/requests/{rid}", headers=H["coord"]).status_code == 404          # rascunho é privado
assert c.get(f"/api/requests/{rid}", headers=H["doc2"]).status_code == 404           # outro docente
act(H["doc"], rid, "approve", 403)                                                    # docente não aprova
act(H["doc"], rid, "register", 403)
step("rascunho invisível a terceiros; docente não aprova")

d = act(H["doc"], rid, "submit")
assert d["status"] == "EM_ANALISE_COORDENACAO" and len(d["signatures"]) == 1
assert d["signatures"][0]["valid"] and len(d["signatures"][0]["hash"]) == 64
step("docente assina e envia → EM_ANÁLISE (assinatura com SHA-256)")
act(H["doc"], rid, "submit", 409)                                                     # transição inválida
act(H["sala"], rid, "register", 404)                                                  # sala ainda não vê
assert c.get(f"/api/requests/{rid}", headers=H["coord2"]).status_code == 404         # coord de outro curso
step("transições inválidas e coordenador de outro curso bloqueados")

assert any(n["request_id"] == rid for n in c.get("/api/notifications", headers=H["coord"]).json()["items"])
assert rid in [x["id"] for x in c.get("/api/requests?inbox=true", headers=H["coord"]).json()]
step("notificação e caixa de entrada do coordenador")

# --- devolução e reenvio
act(H["coord"], rid, "return", 422)                                                   # exige justificativa
d = act(H["coord"], rid, "return", note="Detalhe as turmas impactadas.")
assert d["status"] == "DEVOLVIDA" and d["returns_count"] == 1
upd = c.put(f"/api/requests/{rid}", headers=H["doc"], json=dict(type="PROGRAMADA", start_date=str(start), end_date=str(start + timedelta(days=1)),
            subjects="Banco de Dados — 5SI e 6SI", reason="Congresso", notes="Levarei material", suggested_substitute_id=sub_id))
assert upd.status_code == 200
d = act(H["doc"], rid, "submit")
assert d["status"] == "EM_ANALISE_COORDENACAO" and len(d["signatures"]) == 2
assert [s["valid"] for s in d["signatures"]] == [False, True]    # 1ª assinatura ficou desatualizada após a edição
step("devolvida com justificativa → editada → reenviada (assinatura antiga marcada como desatualizada)")

# --- aprovação com substituto
d = act(H["coord"], rid, "approve", note="Ok", substitute_id=sub_id)
assert d["status"] == "AGUARDANDO_SUBSTITUTO" and d["substitute"]["id"] == sub_id
act(H["sala"], rid, "register", 409)                                                  # ainda sem aceite
step("coordenador aprova e indica substituto → AGUARDANDO_SUBSTITUTO")

# --- substituto
ds = c.get(f"/api/requests/{rid}", headers=H["sub"]).json()
assert ds["reason"] is None and ds["reason_restricted"]                               # LGPD: substituto não vê motivo
act(H["doc"], rid, "accept_substitute", 403)
d = act(H["sub"], rid, "accept_substitute")
assert d["substitute_status"] == "ACEITA"
step("substituto vê dados mínimos (sem motivo) e aceita")

# --- sala
dsala = c.get(f"/api/requests/{rid}", headers=H["sala"]).json()
assert dsala["reason"] is None
d = act(H["sala"], rid, "register")
assert d["status"] == "REGISTRADA_SALA_PROFESSORES"
act(H["sala"], rid, "close", 403)
step("Sala dos Professores registra (sem acesso ao motivo)")

# --- RH
drh = c.get(f"/api/requests/{rid}", headers=H["rh"]).json()
assert drh["reason"] == "Congresso"
assert c.get(f"/api/requests/{rid}/attachment", headers=H["rh"]).status_code == 200
d = act(H["rh"], rid, "close", note="Arquivado")
assert d["status"] == "ENCERRADA_RH" and d["closed_at"]
assert d["allowed_actions"] == []
act(H["rh"], rid, "close", 409)
step("RH encerra → ENCERRADA_RH (estado final sem ações)")

# --- histórico e assinaturas
actions = [e["action"] for e in d["events"]]
for a in ("create", "submit", "return", "approve", "accept_substitute", "register", "close"):
    assert a in actions, a
assert len(d["signatures"]) >= 6 and all(s["ip"] for s in d["signatures"])
step(f"auditoria completa: {len(d['events'])} eventos, {len(d['signatures'])} assinaturas")

# --- PDFs
for who in ("doc", "coord", "sala", "rh"):
    p = c.get(f"/api/requests/{rid}/pdf", headers=H[who])
    assert p.status_code == 200 and p.content[:4] == b"%PDF" and len(p.content) > 3000, who
step("PDF do formulário gerado para docente, coordenador, sala e RH")

# --- notificações chegaram ao docente
ns = c.get("/api/notifications", headers=H["doc"]).json()
assert ns["unread"] > 0
c.post("/api/notifications/read-all", headers=H["doc"])
assert c.get("/api/notifications", headers=H["doc"]).json()["unread"] == 0
step("notificações internas geradas e marcadas como lidas")

# --- relatórios e indicadores
rep = c.get("/api/reports/rh", headers=H["rh"]).json()
assert rep["totals"]["count"] >= 9 and rid in [1000] + [int(r["protocol"].split("-")[-1]) for r in rep["rows"]]
assert all(r["status"] in ("Aprovada", "Aguardando substituto", "Registrada (Sala dos Professores)", "Encerrada (RH)") for r in rep["rows"])
csv_r = c.get("/api/reports/rh.csv?type=PROGRAMADA", headers=H["rh"])
assert csv_r.status_code == 200 and "Protocolo;Docente" in csv_r.text
pdf_r = c.get("/api/reports/rh.pdf", headers=H["rh"])
assert pdf_r.content[:4] == b"%PDF"
assert c.get("/api/reports/rh", headers=H["doc"]).status_code == 403
dash = c.get("/api/dashboard", headers=H["rh"]).json()
assert dash["total"] >= 14 and dash["avg_lead_hours"] and dash["returns_total"] >= 2 and dash["by_status"] and dash["by_type"]
dash_c = c.get("/api/dashboard", headers=H["coord2"]).json()
assert set(dash_c["by_course"]) == {"Administração"}
assert c.get("/api/dashboard", headers=H["doc"]).status_code == 403
step(f"relatórios JSON/CSV/PDF e painel (tempo médio {dash['avg_lead_hours']} h, retrabalho {dash['rework_rate']}%)")

# --- admin e LGPD
assert c.get("/api/requests", headers=H["admin"]).status_code == 403
assert c.get("/api/admin/users", headers=H["doc"]).status_code == 403
nu = c.post("/api/admin/users", headers=H["admin"], json=dict(name="Novo Docente", email="novo@demo.br", password="abc123", role="DOCENTE", course_id=1))
assert nu.status_code == 201
assert c.post("/api/auth/login", json={"email": "novo@demo.br", "password": "abc123"}).status_code == 200
logs = c.get("/api/admin/access-logs", headers=H["admin"]).json()
assert any(l["action"] == "VISUALIZOU_DADOS_SENSIVEIS" for l in logs) and any(l["action"] == "EXPORTOU_RELATORIO_CSV" for l in logs)
step("administração de usuários e log de acesso a dados sensíveis")

assert c.get("/docs").status_code == 200 and c.get("/openapi.json").status_code == 200
step("/docs (Swagger) disponível")
print("\nTODOS OS TESTES PASSARAM")
