import { createContext, useContext, useEffect, useState } from 'react'
import { api, setToken } from './api'

const Ctx = createContext(null)
export const useAuth = () => useContext(Ctx)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [meta, setMeta] = useState({ status: {}, types: {}, roles: {} })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/meta').then(setMeta).catch(() => {})
    const expire = () => setUser(null)
    window.addEventListener('session-expired', expire)
    if (localStorage.getItem('token')) {
      api.get('/auth/me').then(setUser).catch(() => setToken(null)).finally(() => setLoading(false))
    } else setLoading(false)
    return () => window.removeEventListener('session-expired', expire)
  }, [])

  const login = async (email, password) => {
    const r = await api.post('/auth/login', { email, password })
    setToken(r.token)
    setUser(r.user)
    return r.user
  }
  const logout = () => { setToken(null); setUser(null) }

  return <Ctx.Provider value={{ user, meta, loading, login, logout }}>{children}</Ctx.Provider>
}
