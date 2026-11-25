# Controle de Ausências Docentes — protótipo (TCC UniSales)

Requisitos: Python 3.11+, Node 18+ e PostgreSQL 14+.

## Banco de dados (PostgreSQL)
Escolha **uma** das opções:

**A) Com Docker** (mais simples): na pasta `ausencias/`, rode
```bash
docker compose up -d
```
Isso sobe um PostgreSQL 16 com usuário `ausencias`, senha `ausencias` e banco `ausencias`, acessível na porta **5433** do computador (a 5433 evita conflito com um PostgreSQL já instalado no Windows, que usa a 5432).

**B) PostgreSQL instalado no computador** (instalador oficial: https://www.postgresql.org/download/): no `psql` ou no pgAdmin, como usuário `postgres`, rode
```sql
CREATE USER ausencias WITH PASSWORD 'ausencias' CREATEDB;
CREATE DATABASE ausencias OWNER ausencias;
```

Em seguida, copie `backend/.env.example` para `backend/.env`. O arquivo de exemplo usa a porta 5433 (Docker). Na opção B, troque `5433` por `5432` (porta padrão do PostgreSQL instalado) nas duas linhas do `.env`. Se usar outro usuário ou senha, ajuste também.

## Backend (terminal 1)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.seed                                      # cria as tabelas com dados de demonstração (recria do zero)
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
O teste usa um banco separado (`ausencias_test`), criado automaticamente e recriado do zero a cada execução; o banco principal não é alterado.

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
