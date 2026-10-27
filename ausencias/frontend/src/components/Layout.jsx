import { useEffect, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth.jsx'

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  const [unread, setUnread] = useState(0)
  const [pending, setPending] = useState(0)

  useEffect(() => {
    const load = () => {
      api.get('/notifications').then((r) => setUnread(r.unread)).catch(() => {})
      api.get('/requests/inbox-count').then((r) => setPending(r.count)).catch(() => {})
    }
    load()
    const t = setInterval(load, 15000)
    return () => clearInterval(t)
  }, [])

  const r = user.role
  const links = [
    r !== 'ADMIN' && ['/', `Caixa de entrada${pending ? ` (${pending})` : ''}`],
    ['DOCENTE', 'SUBSTITUTO'].includes(r) && ['/solicitacoes/nova', 'Nova solicitação'],
    ['RH', 'COORDENADOR'].includes(r) && ['/indicadores', 'Indicadores'],
    r === 'RH' && ['/relatorios', 'Relatórios'],
    r === 'ADMIN' && ['/admin', 'Administração'],
    r !== 'ADMIN' && ['/notificacoes', `Notificações${unread ? ` (${unread})` : ''}`],
  ].filter(Boolean)

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand"><b>UniSales</b> · Ausências Docentes</div>
        <div className="who">
          <span>{user.name}<small> — {user.role_label}</small></span>
          <button className="btn ghost light" onClick={() => { logout(); nav('/login') }}>Sair</button>
        </div>
      </header>
      <nav className="nav">
        {links.map(([to, label]) => (
          <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => (isActive ? 'active' : '')}>{label}</NavLink>
        ))}
      </nav>
      <main className="container">{children}</main>
      <footer className="footer">
        Protótipo de TCC — dados pessoais tratados conforme a LGPD (Lei 13.709/2018): cada perfil vê apenas o mínimo necessário e acessos a dados sensíveis são registrados.
      </footer>
    </div>
  )
}
