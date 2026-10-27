import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth.jsx'
import Layout from './components/Layout.jsx'
import Login from './pages/Login.jsx'
import Inbox from './pages/Inbox.jsx'
import RequestForm from './pages/RequestForm.jsx'
import RequestDetail from './pages/RequestDetail.jsx'
import Notifications from './pages/Notifications.jsx'
import Reports from './pages/Reports.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Admin from './pages/Admin.jsx'

// Proteção de rotas no frontend (a proteção real está no backend; isto evita telas inúteis).
function Guard({ roles, children }) {
  const { user, loading } = useAuth()
  if (loading) return <p className="center muted">Carregando…</p>
  if (!user) return <Navigate to="/login" replace />
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />
  return <Layout>{children}</Layout>
}

function Home() {
  const { user } = useAuth()
  return user.role === 'ADMIN' ? <Navigate to="/admin" replace /> : <Inbox />
}

const REQUESTERS = ['DOCENTE', 'SUBSTITUTO']

export default function App() {
  const { user } = useAuth()
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
      <Route path="/" element={<Guard><Home /></Guard>} />
      <Route path="/solicitacoes/nova" element={<Guard roles={REQUESTERS}><RequestForm /></Guard>} />
      <Route path="/solicitacoes/:id/editar" element={<Guard roles={REQUESTERS}><RequestForm /></Guard>} />
      <Route path="/solicitacoes/:id" element={<Guard roles={['DOCENTE', 'SUBSTITUTO', 'COORDENADOR', 'SALA_PROFESSORES', 'RH']}><RequestDetail /></Guard>} />
      <Route path="/notificacoes" element={<Guard><Notifications /></Guard>} />
      <Route path="/relatorios" element={<Guard roles={['RH']}><Reports /></Guard>} />
      <Route path="/indicadores" element={<Guard roles={['RH', 'COORDENADOR']}><Dashboard /></Guard>} />
      <Route path="/admin" element={<Guard roles={['ADMIN']}><Admin /></Guard>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
