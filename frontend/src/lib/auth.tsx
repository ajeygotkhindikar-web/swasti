import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, getToken, setToken } from './api'

export type Role = 'individual' | 'coach' | 'counselor' | 'admin'
export interface User {
  user_id: string; full_name: string; email: string; user_role: Role; occupation?: string; industry?: string
  age_group?: string; city?: string; phone_number?: string; registration_date: string; is_synthetic: boolean
}
interface AuthCtx { user: User | null; loading: boolean; login: (email: string, pw: string) => Promise<void>; register: (b: any) => Promise<void>; logout: () => void; refresh: () => Promise<void> }

const Ctx = createContext<AuthCtx>(null!)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const refresh = async () => {
    if (!getToken()) { setUser(null); setLoading(false); return }
    try { setUser(await api<User>('/auth/me')) } catch { setUser(null) } finally { setLoading(false) }
  }
  useEffect(() => { refresh() }, [])
  const login = async (email: string, password: string) => {
    const r = await api<{ access_token: string; user: User }>('/auth/login', { method: 'POST', body: { email, password } })
    setToken(r.access_token); setUser(r.user)
  }
  const register = async (body: any) => {
    const r = await api<{ access_token: string; user: User }>('/auth/register', { method: 'POST', body })
    setToken(r.access_token); setUser(r.user)
  }
  const logout = () => { setToken(null); setUser(null) }
  return <Ctx.Provider value={{ user, loading, login, register, logout, refresh }}>{children}</Ctx.Provider>
}
export const useAuth = () => useContext(Ctx)
