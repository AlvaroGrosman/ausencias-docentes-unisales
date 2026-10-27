import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth.jsx'
import { Alert } from '../components/Common.jsx'

const DEMO = [
  ['docente@demo.br', 'Docente'], ['coord@demo.br', 'Coordenador (SI)'], ['substituto@demo.br', 'Docente substituto'],
  ['sala@demo.br', 'Sala dos Professores'], ['rh@demo.br', 'RH'], ['admin@demo.br', 'Administrador'],
]

export default function Login() {
  const { login } = useAuth()
  const nav = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e, em = email, pw = password) => {
    e?.preventDefault()
    setBusy(true); setError('')
    try { await login(em, pw); nav('/') } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  return (
    <div className="login-wrap">
      <div className="card login">
        <h1>Controle de Ausências Docentes</h1>
        <p className="muted">Centro Universitário Salesiano — UniSales</p>
        <form onSubmit={submit}>
          <label>E-mail<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus /></label>
          <label>Senha<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
          <Alert>{error}</Alert>
          <button className="btn primary block" disabled={busy}>{busy ? 'Entrando…' : 'Entrar'}</button>
        </form>
        <div className="demo">
          <p className="muted small">Acesso rápido para demonstração (senha: demo123)</p>
          <div className="chips">
            {DEMO.map(([em, label]) => (
              <button key={em} type="button" className="btn small" disabled={busy} onClick={() => submit(null, em, 'demo123')}>{label}</button>
            ))}
          </div>
        </div>
        <div className="privacy">
          <b>Nota de privacidade (LGPD)</b>
          <p>Este sistema trata apenas os dados pessoais necessários ao controle de ausências docentes. Cada perfil enxerga somente o mínimo para sua função (por exemplo, o motivo da ausência é restrito ao docente, à Coordenação e ao RH) e todo acesso a dados sensíveis fica registrado em log de auditoria.</p>
        </div>
      </div>
    </div>
  )
}
