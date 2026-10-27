import { useEffect, useState } from 'react'
import { api, download } from '../api'
import { useAuth } from '../auth.jsx'
import { Alert } from '../components/Common.jsx'

const EMPTY = { date_from: '', date_to: '', course_id: '', teacher_id: '', type: '', status: '' }
// RH só enxerga ausências aprovadas em diante (LGPD)
const STATUSES = ['APROVADA', 'AGUARDANDO_SUBSTITUTO', 'REGISTRADA_SALA_PROFESSORES', 'ENCERRADA_RH']

const TotalTable = ({ title, data }) => (
  <div className="card">
    <h3>{title}</h3>
    <table><thead><tr><th></th><th>Solicitações</th><th>Dias</th></tr></thead>
      <tbody>{Object.entries(data).map(([k, v]) => <tr key={k}><td>{k}</td><td>{v.count}</td><td>{v.days}</td></tr>)}</tbody></table>
  </div>
)

export default function Reports() {
  const { meta } = useAuth()
  const [f, setF] = useState(EMPTY)
  const [opts, setOpts] = useState({ teachers: [], courses: [] })
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  const qs = (flt = f) => new URLSearchParams(Object.entries(flt).filter(([, v]) => v)).toString()
  const load = (flt = f) => api.get('/reports/rh?' + qs(flt)).then((r) => { setData(r); setError('') }).catch((e) => setError(e.message))
  useEffect(() => { api.get('/reports/teachers').then(setOpts).catch(() => {}); load() }, [])

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const exp = (ext) => download(`/reports/rh.${ext}?${qs()}`, `relatorio_ausencias.${ext}`, ext === 'pdf').catch((e) => setError(e.message))

  return (
    <>
      <div className="page-head">
        <h2>Relatórios consolidados</h2>
        <div className="actions">
          <button className="btn" onClick={() => exp('csv')}>⬇ CSV</button>
          <button className="btn" onClick={() => exp('pdf')}>📄 PDF</button>
        </div>
      </div>
      <form className="card filters" onSubmit={(e) => { e.preventDefault(); load() }}>
        <label>De<input type="date" value={f.date_from} onChange={set('date_from')} /></label>
        <label>Até<input type="date" value={f.date_to} onChange={set('date_to')} /></label>
        <label>Curso<select value={f.course_id} onChange={set('course_id')}><option value="">Todos</option>{opts.courses.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
        <label>Docente<select value={f.teacher_id} onChange={set('teacher_id')}><option value="">Todos</option>{opts.teachers.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select></label>
        <label>Tipo<select value={f.type} onChange={set('type')}><option value="">Todos</option>{Object.entries(meta.types).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Status<select value={f.status} onChange={set('status')}><option value="">Todos</option>{STATUSES.map((s) => <option key={s} value={s}>{meta.status[s]}</option>)}</select></label>
        <div className="actions"><button className="btn primary">Filtrar</button><button type="button" className="btn" onClick={() => { setF(EMPTY); load(EMPTY) }}>Limpar</button></div>
      </form>
      <Alert>{error}</Alert>
      {data && (
        <>
          <div className="kpis">
            <div className="card kpi"><small>Solicitações</small><b>{data.totals.count}</b></div>
            <div className="card kpi"><small>Dias de ausência</small><b>{data.totals.days}</b></div>
          </div>
          <div className="grid3">
            <TotalTable title="Por tipo" data={data.totals.by_type} />
            <TotalTable title="Por curso" data={data.totals.by_course} />
            <TotalTable title="Por status" data={data.totals.by_status} />
          </div>
          <div className="card">
            <h3>Detalhamento</h3>
            <div className="scroll"><table>
              <thead><tr><th>Protocolo</th><th>Docente</th><th>Curso</th><th>Tipo</th><th>Início</th><th>Fim</th><th>Dias</th><th>Status</th><th>Devol.</th></tr></thead>
              <tbody>{data.rows.map((r) => <tr key={r.protocol}><td>{r.protocol}</td><td>{r.teacher}</td><td>{r.course}</td><td>{r.type}</td><td>{r.start_date}</td><td>{r.end_date}</td><td>{r.days}</td><td>{r.status}</td><td>{r.returns}</td></tr>)}</tbody>
            </table></div>
            {data.rows.length === 0 && <p className="muted">Nenhum registro para os filtros informados.</p>}
          </div>
        </>
      )}
    </>
  )
}
