import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, download, fmtDate, fmtDT } from '../api'
import { Alert, StatusBadge, Timeline } from '../components/Common.jsx'

export default function RequestDetail() {
  const { id } = useParams()
  const [req, setReq] = useState(null)
  const [note, setNote] = useState('')
  const [sub, setSub] = useState('')
  const [subs, setSubs] = useState([])
  const [error, setError] = useState('')
  const [ok, setOk] = useState('')
  const [busy, setBusy] = useState(false)

  const apply = (r) => { setReq(r); setSub(r.suggested_substitute?.id ?? '') }
  useEffect(() => {
    api.get(`/requests/${id}`).then(apply).catch((e) => setError(e.message))
  }, [id])
  useEffect(() => {
    if (req?.allowed_actions.some((a) => a.needs_substitute) && !subs.length)
      api.get('/substitute-candidates').then((l) => setSubs(l.filter((s) => s.id !== req.teacher.id))).catch(() => {})
  }, [req])

  const run = async (a) => {
    if (a.needs_note && !note.trim()) return setError('Informe a justificativa no campo de observação.')
    if (a.action === 'cancel' && !confirm('Cancelar esta solicitação?')) return
    setBusy(true); setError(''); setOk('')
    try {
      const r = await api.post(`/requests/${id}/actions/${a.action}`, { note: note || null, substitute_id: a.needs_substitute && sub ? Number(sub) : null })
      apply(r); setNote(''); setOk(`Ação concluída: ${a.label}.`)
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  const safe = (fn) => () => fn().catch((e) => setError(e.message))

  if (!req) return error ? <Alert>{error}</Alert> : <p className="muted">Carregando…</p>
  const needsNote = req.allowed_actions.some((a) => a.needs_note || ['approve', 'accept_substitute', 'register', 'close', 'cancel'].includes(a.action))
  const hasSubPick = req.allowed_actions.some((a) => a.needs_substitute)

  return (
    <>
      <p><Link to="/">← Voltar</Link></p>
      <div className="page-head">
        <h2>{req.protocol} <StatusBadge status={req.status} /></h2>
        <div className="actions">
          {req.can_edit && <Link className="btn" to={`/solicitacoes/${req.id}/editar`}>Editar</Link>}
          <button className="btn" onClick={safe(() => download(`/requests/${req.id}/pdf`, `${req.protocol}.pdf`, true))}>📄 Gerar PDF</button>
        </div>
      </div>

      <div className="card"><h3>Andamento</h3><Timeline req={req} /></div>

      <div className="card">
        <h3>Dados da solicitação</h3>
        <dl className="kv">
          <dt>Docente</dt><dd>{req.teacher.name}</dd>
          <dt>Curso</dt><dd>{req.course.name}</dd>
          <dt>Tipo</dt><dd>{req.type_label}</dd>
          <dt>Período</dt><dd>{fmtDate(req.start_date)} a {fmtDate(req.end_date)} ({req.days} dia{req.days > 1 ? 's' : ''})</dd>
          <dt>Disciplinas/turmas</dt><dd>{req.subjects}</dd>
          <dt>Motivo</dt><dd>{req.reason_restricted ? <i className="muted">Restrito (LGPD) — visível apenas ao docente, à Coordenação e ao RH.</i> : req.reason}</dd>
          {!req.reason_restricted && req.notes && <><dt>Observações</dt><dd>{req.notes}</dd></>}
          {req.has_attachment && <><dt>Anexo</dt><dd><button className="link" onClick={safe(() => download(`/requests/${req.id}/attachment`, req.attachment_name))}>{req.attachment_name}</button></dd></>}
          <dt>Substituto</dt>
          <dd>{req.substitute ? `${req.substitute.name} — ${req.substitute_status === 'ACEITA' ? 'aceitou' : 'aguardando resposta'}` : req.suggested_substitute ? `Sugerido: ${req.suggested_substitute.name}` : 'Não indicado'}</dd>
        </dl>
      </div>

      {req.allowed_actions.length > 0 && (
        <div className="card action-box">
          <h3>Ações disponíveis para você</h3>
          {hasSubPick && (
            <label>Professor substituto
              <select value={sub} onChange={(e) => setSub(e.target.value)}>
                <option value="">— sem substituto —</option>
                {subs.map((s) => <option key={s.id} value={s.id}>{s.name}{s.course_name ? ` (${s.course_name})` : ''}</option>)}
              </select>
            </label>
          )}
          {needsNote && <label>Observação / justificativa<textarea rows="2" value={note} onChange={(e) => setNote(e.target.value)} placeholder="Obrigatória para devolver, recusar ou declinar" /></label>}
          <Alert>{error}</Alert><Alert kind="ok">{ok}</Alert>
          <div className="actions wrap">
            {req.allowed_actions.map((a) => (
              <button key={a.action} disabled={busy} onClick={() => run(a)}
                className={`btn ${['approve', 'submit', 'accept_substitute', 'register', 'close'].includes(a.action) ? 'primary' : ['reject', 'cancel', 'decline_substitute'].includes(a.action) ? 'danger' : ''}`}>
                {a.label}
              </button>
            ))}
          </div>
        </div>
      )}
      {req.allowed_actions.length === 0 && <><Alert>{error}</Alert><Alert kind="ok">{ok}</Alert></>}

      <div className="card">
        <h3>Assinaturas eletrônicas <small className="muted">(simuladas)</small></h3>
        {req.signatures.length === 0 ? <p className="muted">Ainda não assinada.</p> : (
          <div className="scroll"><table>
            <thead><tr><th>Assinante</th><th>Papel</th><th>Data/hora</th><th>IP</th><th>Hash SHA-256 do conteúdo</th><th>Situação</th></tr></thead>
            <tbody>{req.signatures.map((s) => (
              <tr key={s.id}><td>{s.user}</td><td>{s.role_label}</td><td>{fmtDT(s.signed_at)}</td><td>{s.ip}</td>
                <td><code className="hash">{s.hash}</code></td>
                <td>{s.valid ? <span className="ok-txt">Íntegra</span> : <span className="bad-txt">Conteúdo alterado depois</span>}</td></tr>
            ))}</tbody>
          </table></div>
        )}
      </div>

      <div className="card">
        <h3>Histórico (auditoria)</h3>
        <div className="scroll"><table>
          <thead><tr><th>Data/hora</th><th>Responsável</th><th>Ação</th><th>Status</th><th>Observação</th></tr></thead>
          <tbody>{req.events.map((e) => (
            <tr key={e.id}><td>{fmtDT(e.created_at)}</td><td>{e.user}{e.role_label ? <small className="muted"> · {e.role_label}</small> : ''}</td><td>{e.action_label}</td>
              <td>{e.from_status && e.from_status !== e.to_status ? <>{e.from_status.replaceAll('_', ' ')} → </> : null}{e.to_status.replaceAll('_', ' ')}</td><td>{e.note}</td></tr>
          ))}</tbody>
        </table></div>
      </div>
    </>
  )
}
