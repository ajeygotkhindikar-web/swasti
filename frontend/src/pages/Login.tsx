import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { Emblem } from '../components/Logo'
import { useAuth } from '../lib/auth'

const DEMO = [
  ['Individual', 'priya@swasti.demo'], ['Coach', 'coach@swasti.demo'],
  ['Counsellor', 'counselor@swasti.demo'], ['Admin', 'admin@swasti.demo'],
]

export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden overflow-hidden bg-fillsoft p-12 text-ink lg:flex lg:flex-col lg:justify-between" style={{ backgroundImage: 'radial-gradient(circle at 85% 90%, rgb(var(--fill)) 0, transparent 55%)' }}>
        <div className="flex items-center gap-3"><div className="rounded-full bg-surface p-1 shadow-card"><Emblem size={44} /></div><span className="font-display text-xl tracking-[0.2em] text-teal">SWASTI</span></div>
        <div>
          <h1 className="font-display text-5xl leading-tight">Balance Within.<br />Harmony Around.<br /><span className="text-saffron">Well-being for All.</span></h1>
          <p className="mt-6 max-w-md text-muted">A 360° view across fourteen dimensions of life — mind, body, money, family, community, culture and more — with small, evidence-informed steps to keep them in balance.</p>
        </div>
        <p className="text-xs text-muted">Balanced professionals · Healthy families · Compassionate communities · A sustainable society</p>
        <svg className="pointer-events-none absolute -right-40 -bottom-40 opacity-70" width="560" height="560" viewBox="0 0 100 100" aria-hidden>
          {Array.from({ length: 14 }, (_, i) => { const a = (i / 14) * Math.PI * 2; return <circle key={i} cx={50 + 40 * Math.cos(a)} cy={50 + 40 * Math.sin(a)} r="3" fill="rgb(var(--fill-strong))" /> })}
          <circle cx="50" cy="50" r="46" stroke="rgb(var(--fill-strong))" fill="none" />
        </svg>
      </div>
      <div className="flex items-center justify-center p-6">{children}</div>
    </div>
  )
}

export default function Login() {
  const { user, login } = useAuth()
  const nav = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  if (user) return <Navigate to="/" replace />
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null)
    try { await login(email, password); nav('/') } catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  return (
    <AuthShell>
      <form onSubmit={submit} className="w-full max-w-sm space-y-4">
        <div className="lg:hidden mb-4 flex justify-center"><Emblem size={64} /></div>
        <h2 className="text-3xl font-semibold">Welcome back</h2>
        <p className="text-sm text-muted">Sign in to continue your wellness journey.</p>
        <div><label className="label" htmlFor="email">Email</label><input id="email" className="input" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></div>
        <div><label className="label" htmlFor="pw">Password</label><input id="pw" className="input" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required /></div>
        {err && <p className="text-sm" style={{ color: 'var(--lv-attention)' }} role="alert">{err}</p>}
        <button className="btn-primary w-full" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
        <p className="text-center text-sm text-muted">New here? <Link to="/register" className="font-semibold text-teal">Create an account</Link></p>
        <div className="rounded-2xl border border-dashed border-line p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">Synthetic demo accounts · password Demo@1234</p>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {DEMO.map(([r, e]) => <button type="button" key={e} className="btn-ghost text-xs" onClick={() => { setEmail(e); setPassword('Demo@1234') }}>{r}</button>)}
          </div>
        </div>
      </form>
    </AuthShell>
  )
}
