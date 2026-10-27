import { useAuth } from '../auth.jsx'

export function StatusBadge({ status, label }) {
  const { meta } = useAuth()
  return <span className={`badge st-${status}`}>{label || meta.status[status] || status}</span>
}

export const Alert = ({ kind = 'error', children }) => (children ? <div className={`alert ${kind}`}>{children}</div> : null)

// Linha do tempo visual do fluxo (estado atual + data de cada etapa já cumprida).
const FLOW = ['RASCUNHO', 'ENVIADA', 'EM_ANALISE_COORDENACAO', 'APROVADA', 'AGUARDANDO_SUBSTITUTO', 'REGISTRADA_SALA_PROFESSORES', 'ENCERRADA_RH']
const BRANCH = ['DEVOLVIDA', 'RECUSADA', 'CANCELADA']

export function Timeline({ req }) {
  const { meta } = useAuth()
  const reached = {}
  req.events.forEach((e) => { reached[e.to_status] ??= e.created_at })
  const usesSub = !!reached.AGUARDANDO_SUBSTITUTO
  let steps = FLOW.filter((s) => s !== 'AGUARDANDO_SUBSTITUTO' || usesSub).map((s) => ({ key: s, at: reached[s] }))
  const branch = BRANCH.includes(req.status)
  if (branch) steps = [...steps.filter((s) => s.at), { key: req.status, at: reached[req.status] }]
  return (
    <ol className="timeline">
      {steps.map((s, i) => {
        let cls = 'todo'
        if (s.at) cls = 'done'
        if (!branch && s.key === req.status && req.status !== 'ENCERRADA_RH') cls = 'current'
        if (branch && i === steps.length - 1) cls = 'bad'
        return (
          <li key={s.key} className={cls}>
            <span className="dot">{cls === 'done' ? '✓' : cls === 'bad' ? '!' : i + 1}</span>
            <span className="tl-label">{meta.status[s.key]}</span>
            <small>{s.at ? new Date(s.at).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : ''}</small>
          </li>
        )
      })}
    </ol>
  )
}
