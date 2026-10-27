import { useEffect, useState } from 'react'
import { api, fmtHours } from '../api'
import { useAuth } from '../auth.jsx'
import { Alert } from '../components/Common.jsx'

function Bars({ data }) {
  const max = Math.max(1, ...Object.values(data))
  return (
    <div className="bars">
      {Object.entries(data).map(([k, v]) => (
        <div className="bar-row" key={k}>
          <span className="bar-label">{k}</span>
          <div className="bar-track"><div className="bar-fill" style={{ width: `${(v / max) * 100}%` }} /></div>
          <b>{v}</b>
        </div>
      ))}
    </div>
  )
}

export default function Dashboard() {
  const { user } = useAuth()
  const [d, setD] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => { api.get('/dashboard').then(setD).catch((e) => setError(e.message)) }, [])
  if (!d) return error ? <Alert>{error}</Alert> : <p className="muted">Carregando…</p>
  const kpis = [
    ['Tempo médio de tramitação', fmtHours(d.avg_lead_hours), `envio → encerramento (${d.closed} processos encerrados)`],
    ['Decisão da Coordenação', fmtHours(d.avg_coord_decision_hours), 'tempo médio até aprovar, devolver ou recusar'],
    ['Devoluções (retrabalho)', d.returns_total, `${d.requests_with_return} solicitações devolvidas ao menos 1 vez`],
    ['Taxa de retrabalho', `${d.rework_rate}%`, 'solicitações com devolução'],
    ['Solicitações no período', d.total, user.role === 'COORDENADOR' ? 'do seu curso' : 'de todos os cursos'],
  ]
  return (
    <>
      <h2>Indicadores</h2>
      <p className="muted small">Indicadores agregados (sem dados pessoais) que sustentam a hipótese do estudo: redução do tempo de tramitação e do retrabalho em relação ao fluxo em papel.</p>
      <div className="kpis">
        {kpis.map(([t, v, s]) => <div className="card kpi" key={t}><small>{t}</small><b>{v}</b><span className="muted small">{s}</span></div>)}
      </div>
      <div className="grid2">
        <div className="card"><h3>Por status</h3><Bars data={d.by_status} /></div>
        <div className="card"><h3>Por tipo</h3><Bars data={d.by_type} /><h3 style={{ marginTop: 18 }}>Por curso</h3><Bars data={d.by_course} /></div>
      </div>
    </>
  )
}
