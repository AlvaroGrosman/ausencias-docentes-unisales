import { useEffect, useState } from 'react'
import { api, fmtDT } from '../api'
import { useAuth } from '../auth.jsx'
import { Alert } from '../components/Common.jsx'

const BLANK = { id: null, name: '', email: '', password: '', role: 'DOCENTE', course_id: '', active: true }

export default function Admin() {
  const { meta } = useAuth()
  const [tab, setTab] = useState('users')
  const [users, setUsers] = useState([])
  const [courses, setCourses] = useState([])
  const [logs, setLogs] = useState([])
  const [form, setForm] = useState(null)
  const [course, setCourse] = useState('')
  const [error, setError] = useState('')
  const [ok, setOk] = useState('')

  const load = () => {
    api.get('/admin/users').then(setUsers).catch((e) => setError(e.message))
    api.get('/admin/courses').then(setCourses).catch(() => {})
    api.get('/admin/access-logs').then(setLogs).catch(() => {})
  }
  useEffect(load, [])
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  const saveUser = async (e) => {
    e.preventDefault(); setError(''); setOk('')
    const body = { name: form.name, email: form.email, role: form.role, active: form.active, password: form.password || null, course_id: form.course_id ? Number(form.course_id) : null }
    try {
      form.id ? await api.put(`/admin/users/${form.id}`, body) : await api.post('/admin/users', body)
      setForm(null); setOk('Usuário salvo.'); load()
    } catch (err) { setError(err.message) }
  }
  const addCourse = async (e) => {
    e.preventDefault(); setError('')
    try { await api.post('/admin/courses', { name: course }); setCourse(''); load() } catch (err) { setError(err.message) }
  }

  return (
    <>
      <h2>Administração</h2>
      <div className="tabs">
        {[['users', 'Usuários'], ['courses', 'Cursos'], ['logs', 'Log de acesso (LGPD)']].map(([k, l]) => <button key={k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)}>{l}</button>)}
      </div>
      <Alert>{error}</Alert><Alert kind="ok">{ok}</Alert>

      {tab === 'users' && (
        <>
          {form ? (
            <form className="card form" onSubmit={saveUser}>
              <h3>{form.id ? 'Editar usuário' : 'Novo usuário'}</h3>
              <div className="grid2">
                <label>Nome<input value={form.name} onChange={set('name')} required /></label>
                <label>E-mail<input type="email" value={form.email} onChange={set('email')} required /></label>
                <label>Perfil<select value={form.role} onChange={set('role')}>{Object.entries(meta.roles).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
                <label>Curso<select value={form.course_id} onChange={set('course_id')}><option value="">—</option>{courses.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
                <label>Senha {form.id && <small className="muted">(deixe vazio para manter)</small>}<input type="password" minLength="6" value={form.password} onChange={set('password')} required={!form.id} /></label>
                <label className="check"><input type="checkbox" checked={form.active} onChange={set('active')} /> Ativo</label>
              </div>
              <div className="actions"><button type="button" className="btn" onClick={() => setForm(null)}>Cancelar</button><button className="btn primary">Salvar</button></div>
            </form>
          ) : <button className="btn primary" onClick={() => setForm(BLANK)}>+ Novo usuário</button>}
          <div className="card scroll"><table>
            <thead><tr><th>Nome</th><th>E-mail</th><th>Perfil</th><th>Curso</th><th>Ativo</th><th></th></tr></thead>
            <tbody>{users.map((u) => (
              <tr key={u.id}><td>{u.name}</td><td>{u.email}</td><td>{u.role_label}</td><td>{u.course_name || '—'}</td><td>{u.active ? 'Sim' : 'Não'}</td>
                <td><button className="link" onClick={() => setForm({ ...u, password: '', course_id: u.course_id ?? '' })}>Editar</button></td></tr>
            ))}</tbody>
          </table></div>
        </>
      )}

      {tab === 'courses' && (
        <div className="card">
          <form className="inline" onSubmit={addCourse}><input placeholder="Nome do novo curso" value={course} onChange={(e) => setCourse(e.target.value)} required /><button className="btn primary">Adicionar</button></form>
          <ul>{courses.map((c) => <li key={c.id}>{c.name}</li>)}</ul>
        </div>
      )}

      {tab === 'logs' && (
        <div className="card scroll">
          <p className="muted small">Últimos acessos de terceiros a dados sensíveis (motivo, anexos, PDFs) e exportações de relatórios.</p>
          <table>
            <thead><tr><th>Data/hora</th><th>Usuário</th><th>Ação</th><th>Recurso</th><th>IP</th></tr></thead>
            <tbody>{logs.map((l) => <tr key={l.id}><td>{fmtDT(l.created_at)}</td><td>{l.user}</td><td>{l.action}</td><td>{l.resource}</td><td>{l.ip}</td></tr>)}</tbody>
          </table>
          {logs.length === 0 && <p className="muted">Nenhum acesso registrado ainda.</p>}
        </div>
      )}
    </>
  )
}
