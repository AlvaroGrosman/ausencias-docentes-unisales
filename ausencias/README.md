# Controle de Ausências Docentes — protótipo (TCC UniSales)

Requisitos: Python 3.11+ e Node 18+.

## Backend (terminal 1)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.seed                                      # cria o banco com dados de demonstração (recria do zero)
uvicorn app.main:app --reload --port 8000
```
API e documentação: http://localhost:8000/docs

## Frontend (terminal 2)
```bash
cd frontend
npm install
npm run dev
```
Abra http://localhost:5173

## Teste automático do fluxo completo (opcional)
```bash
cd backend && python test_flow.py
```

## Usuários de teste (senha de todos: `demo123`)
| Perfil | E-mail |
|---|---|
| Docente (Sistemas de Informação) | docente@demo.br · docente2@demo.br |
| Docente (Administração) | docente3@demo.br |
| Coordenador SI / ADM | coord@demo.br / coord2@demo.br |
| Docente substituto | substituto@demo.br |
| Sala dos Professores | sala@demo.br |
| RH | rh@demo.br |
| Administrador | admin@demo.br |
