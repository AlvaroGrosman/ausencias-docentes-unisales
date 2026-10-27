import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'
import { Alert } from '../components/Common.jsx'

const today = () => new Date().toISOString().slice(0, 10)
const EMPTY = { type: 'PROGRAMADA', start_date: today(), end_date: today(), subjects: '', reason: '', notes: '', suggested_substitute_id: '' }

export default function RequestForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const [f, setF] = useState(EMPTY)
  const [subs, setSubs] = useState([])
  const [file, setFile] = useState(null)
  const [current, setCurrent] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.get('/substitute-candidates').then(setSubs).catch(() => {})
    if (id) {
      api.get(`/requests/${id}`).then((r) => {
        if (!r.can_edit) return nav(`/solicitacoes/${id}`, { replace: true })
        setCurrent(r)
        setF({ type: r.type, start_date: r.start_date, end_date: r.end_date, subjects: r.subjects, reason: r.reason || '', notes: r.notes || '',
               suggested_substitute_id: r.suggested_substitute?.id ?? '' })
      }).catch((e) => setError(e.message))
    }
  }, [id])

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  const save = async (e) => {
    e.preventDefault()
    setBusy(true); setError('')
    const body = { ...f, notes: f.notes || null, suggested_substitute_id: f.suggested_substitute_id ? Number(f.suggested_substitute_id) : null }
    try {
      const r = id ? await api.put(`/requests/${id}`, body) : await api.post('/requests', body)
      if (file) await api.upload(`/requests/${r.id}/attachment`, file)
      nav(`/solicitacoes/${r.id}`)
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  return (
    <>
      <h2>{id ? 'Editar solicitação' : 'Nova solicitação de ausência'}</h2>
      <form className="card form" onSubmit={save}>
        <div className="radio-row">
          {[['PROGRAMADA', 'Programada', 'compromisso conhecido, com antecedência'], ['NAO_PROGRAMADA', 'Não programada', 'imprevisto — pode ser registrada depois']].map(([v, l, d]) => (
            <label key={v} className={`radio ${f.type === v ? 'on' : ''}`}>
              <input type="radio" name="type" value={v} checked={f.type === v} onChange={set('type')} />
              <b>{l}</b><small>{d}</small>
            </label>
          ))}
        </div>
        <div className="grid2">
          <label>Data inicial<input type="date" value={f.start_date} onChange={set('start_date')} required /></label>
          <label>Data final<input type="date" value={f.end_date} min={f.start_date} onChange={set('end_date')} required /></label>
        </div>
        <label>Disciplinas / turmas afetadas
          <textarea rows="2" value={f.subjects} onChange={set('subjects')} required placeholder="Ex.: Banco de Dados II — turma 7SI (terças, 19h)" />
        </label>
        <label>Motivo <small className="muted">(visível só a você, à Coordenação e ao RH)</small>
          <textarea rows="3" value={f.reason} onChange={set('reason')} required />
        </label>
        <label>Observações (opcional)<textarea rows="2" value={f.notes} onChange={set('notes')} /></label>
        <label>Substituto sugerido (opcional)
          <select value={f.suggested_substitute_id} onChange={set('suggested_substitute_id')}>
            <option value="">— nenhum —</option>
            {subs.map((s) => <option key={s.id} value={s.id}>{s.name}{s.course_name ? ` (${s.course_name})` : ''}</option>)}
          </select>
        </label>
        <label>Anexo (opcional — PDF, PNG ou JPG até 5 MB)
          <input type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={(e) => setFile(e.target.files[0] || null)} />
          {current?.attachment_name && !file && <small className="muted">Anexo atual: {current.attachment_name}</small>}
        </label>
        <Alert>{error}</Alert>
        <div className="actions">
          <button type="button" className="btn" onClick={() => nav(-1)}>Cancelar</button>
          <button className="btn primary" disabled={busy}>{busy ? 'Salvando…' : 'Salvar rascunho'}</button>
        </div>
        <p className="muted small">Depois de salvar, abra a solicitação e clique em “Assinar e enviar” para encaminhá-la à Coordenação.</p>
      </form>
    </>
  )
}
