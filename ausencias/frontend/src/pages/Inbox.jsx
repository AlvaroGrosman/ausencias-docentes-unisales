import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, fmtDate, fmtDT } from '../api'
import { useAuth } from '../auth.jsx'
import { Alert, StatusBadge } from '../components/Common.jsx'

export default function Inbox() {
  const { user, meta } = useAuth()
  const [tab, setTab] = useState('pending')
  const [status, setStatus] = useState('')
  const [rows, setRows] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setRows(null)
    const qs = new URLSearchParams()
    if (tab === 'pending') qs.set('inbox', 'true')
    if (status) qs.set('status', status)
    api.get('/requests?' + qs).then(setRows).catch((e) => setError(e.message))
  }, [tab, status])

  const canCreate = ['DOCENTE', 'SUBSTITUTO'].includes(user.role)
  return (
    <>
      <div className="page-head">
        <h2>Caixa de entrada</h2>
        {canCreate && <Link className="btn primary" to="/solicitacoes/nova">+ Nova solicitação</Link>}
      </div>
      <div className="card privacy slim">
        <b>Privacidade (LGPD):</b> você vê apenas as solicitações pertinentes ao seu perfil e somente os dados necessários à sua função.
      </div>
      <div className="toolbar">
        <div className="tabs">
          <button className={tab === 'pending' ? 'active' : ''} onClick={() => setTab('pending')}>Pendências comigo</button>
          <button className={tab === 'all' ? 'active' : ''} onClick={() => setTab('all')}>Todas</button>
        </div>
        <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filtrar por status">
          <option value="">Todos os status</option>
          {Object.entries(meta.status).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>
      <Alert>{error}</Alert>
      {rows === null ? <p className="muted">Carregando…</p> : rows.length === 0 ? (
        <div className="card empty">{tab === 'pending' ? 'Nenhuma pendência para você. 🎉' : 'Nenhuma solicitação encontrada.'}</div>
      ) : (
        <div className="list">
          {rows.map((r) => (
            <Link key={r.id} to={`/solicitacoes/${r.id}`} className="card item">
              <div className="item-top">
                <b>{r.protocol}</b>
                <StatusBadge status={r.status} />
              </div>
              <div>{r.teacher.name} <span className="muted">· {r.course.name}</span></div>
              <div className="muted small">
                {r.type_label} · {fmtDate(r.start_date)} a {fmtDate(r.end_date)} ({r.days} dia{r.days > 1 ? 's' : ''}) · {r.subjects}
              </div>
              <div className="muted small">Atualizada em {fmtDT(r.updated_at)}{r.returns_count ? ` · ${r.returns_count} devolução(ões)` : ''}</div>
            </Link>
          ))}
        </div>
      )}
    </>
  )
}
