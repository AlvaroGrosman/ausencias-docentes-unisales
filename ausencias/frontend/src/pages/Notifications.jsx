import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, fmtDT } from '../api'
import { Alert } from '../components/Common.jsx'

export default function Notifications() {
  const nav = useNavigate()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const load = () => api.get('/notifications').then(setData).catch((e) => setError(e.message))
  useEffect(() => { load() }, [])

  const open = async (n) => {
    if (!n.read) await api.post(`/notifications/${n.id}/read`).catch(() => {})
    if (n.request_id) nav(`/solicitacoes/${n.request_id}`)
  }
  return (
    <>
      <div className="page-head">
        <h2>Notificações</h2>
        <button className="btn" onClick={() => api.post('/notifications/read-all').then(load)}>Marcar todas como lidas</button>
      </div>
      <p className="muted small">Notificações internas simuladas (o protótipo não envia e-mails).</p>
      <Alert>{error}</Alert>
      {!data ? <p className="muted">Carregando…</p> : data.items.length === 0 ? <div className="card empty">Sem notificações.</div> : (
        <div className="list">
          {data.items.map((n) => (
            <button key={n.id} className={`card item notif ${n.read ? '' : 'unread'}`} onClick={() => open(n)}>
              <div>{n.message}</div><div className="muted small">{fmtDT(n.created_at)}</div>
            </button>
          ))}
        </div>
      )}
    </>
  )
}
