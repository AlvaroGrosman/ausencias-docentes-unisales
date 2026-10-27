"""Ponto de entrada da API. Documentação automática em /docs."""
from datetime import datetime

from fastapi import FastAPI
from fastapi.encoders import ENCODERS_BY_TYPE
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .database import Base, engine
from .routers import admin, auth, lookups, notifications, reports, requests

# Datas internas são UTC "naive": serializa com 'Z' para o navegador converter para o fuso local.
ENCODERS_BY_TYPE[datetime] = lambda d: d.isoformat() + "Z"

Base.metadata.create_all(engine)

app = FastAPI(title="Controle de Ausências Docentes — UniSales (protótipo TCC)",
              description="Workflow digital de ausências docentes: Docente → Coordenação → Substituto → Sala dos Professores → RH.",
              version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])
for r in (auth, requests, notifications, reports, admin, lookups):
    app.include_router(r.router)


@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc: RequestValidationError):
    """Mensagens de validação legíveis, em português."""
    msgs = []
    for e in exc.errors():
        field = ".".join(str(x) for x in e["loc"] if x not in ("body", "query"))
        msg = e["msg"].replace("Value error, ", "")
        msgs.append(f"{field}: {msg}" if field and e["type"] != "value_error" else msg)
    return JSONResponse(status_code=422, content={"detail": " | ".join(msgs)})


@app.get("/api/health", tags=["Apoio"])
def health():
    return {"status": "ok"}
