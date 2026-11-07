import { useState } from 'react'
import { Download, ShieldCheck, Trash2, UserPlus, XCircle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useApi } from '../lib/hooks'
import { useAuth } from '../lib/auth'
import { ErrorNote, PageHeader, Spinner } from '../components/ui'

const CONSENTS: [string, string, string][] = [
  ['data_processing', 'Process my wellness data', 'Required to calculate scores and recommendations. Withdrawing stops new processing; delete your account to erase data.'],
  ['ai_analysis', 'AI wording of summaries', 'Lets a language model rephrase agent summaries. Only scores and dimension names are sent — never identity or comments.'],
  ['interview_transcription', 'Interview voice-to-text', 'Allows a consented coach to save an encrypted transcript of an interview with you.'],
  ['push_notifications', 'Push notifications', 'Gentle reminders on this device. You can turn these off at any time.'],
  ['anonymized_research', 'Anonymised research', 'Include my de-identified data in aggregated statistics (groups of 5+ only).'],
]
const SCOPES: [string, string][] = [['assessments', 'Scores, dashboard & reviews'], ['interviews', 'Conduct & view interviews'], ['reports', 'Download PDF reports'], ['observations', 'Counsellor professional notes']]

export default function Privacy() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  const { data: consents, reload } = useApi<any>('/consents')
  const isInd = user?.user_role === 'individual'
  const { data: grants, reload: reloadGrants } = useApi<any[]>('/access-grants')
  const { data: pros } = useApi<any[]>(isInd ? '/professionals' : null)
  const [g, setG] = useState({ grantee_id: '', scopes: ['assessments'] as string[], expires_in_days: 180 })
  const [err, setErr] = useState<string | null>(null)
  if (!consents) return <Spinner />
  const setConsent = async (t: string, granted: boolean) => {
    if (granted && t === 'push_notifications' && 'Notification' in window) { const p = await Notification.requestPermission(); if (p !== 'granted') return }
    await api('/consents', { method: 'POST', body: { consent_type: t, granted } }); reload()
  }
  const grant = async () => { setErr(null); try { await api('/access-grants', { method: 'POST', body: g }); reloadGrants() } catch (e: any) { setErr(e.message) } }
  const revoke = async (id: string) => { await api(`/access-grants/${id}`, { method: 'DELETE' }); reloadGrants() }
  const exportData = async () => {
    const d = await api('/me/export'); const b = new Blob([JSON.stringify(d, null, 2)], { type: 'application/json' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = 'swasti-my-data.json'; a.click()
  }
  const del = async () => { if (!confirm('Permanently delete your account and wellness data? This cannot be undone.')) return; await api('/me', { method: 'DELETE' }); logout(); nav('/login') }
  const pro = pros?.find((p) => p.user_id === g.grantee_id)
  return (
    <div className="max-w-4xl space-y-6">
      <PageHeader title="Privacy & Consent" subtitle="You decide who sees your wellness information. Your employer never has access to your individual results. Every access is logged." />
      <section className="card p-5">
        <h2 className="text-lg font-semibold">Your consents</h2>
        <ul className="mt-3 divide-y divide-line">
          {CONSENTS.map(([k, t, d]) => {
            const on = consents.current[k]?.granted
            return (
              <li key={k} className="flex items-start gap-4 py-3">
                <div className="flex-1"><div className="text-sm font-semibold">{t}</div><div className="text-xs text-muted">{d}</div>{consents.current[k]?.timestamp && <div className="text-[11px] text-muted">v{consents.current[k].version} · {consents.current[k].timestamp.slice(0, 10)}</div>}</div>
                <button role="switch" aria-checked={on} aria-label={t} onClick={() => setConsent(k, !on)} className={`relative h-7 w-12 shrink-0 rounded-full transition ${on ? 'bg-fillstrong' : 'bg-line'}`}>
                  <span className={`absolute top-1 h-5 w-5 rounded-full bg-surface shadow transition ${on ? 'left-6' : 'left-1'}`} />
                </button>
              </li>
            )
          })}
        </ul>
      </section>

      {isInd && (
        <section className="card space-y-4 p-5">
          <h2 className="text-lg font-semibold">Share with a coach or counsellor</h2>
          <p className="text-sm text-muted">Access is limited to what you choose, can expire automatically, and ends the moment you revoke it.</p>
          <div className="grid gap-3 sm:grid-cols-3">
            <select className="input sm:col-span-2" value={g.grantee_id} onChange={(e) => setG({ ...g, grantee_id: e.target.value, scopes: g.scopes.filter((s) => s !== 'observations') })} aria-label="Professional">
              <option value="">Choose a coach or counsellor…</option>
              {pros?.map((p) => <option key={p.user_id} value={p.user_id}>{p.full_name} — {p.user_role === 'counselor' ? 'Counsellor' : 'Coach'}</option>)}
            </select>
            <select className="input" value={g.expires_in_days} onChange={(e) => setG({ ...g, expires_in_days: +e.target.value })} aria-label="Duration">
              {[30, 90, 180, 365].map((d) => <option key={d} value={d}>Expires in {d} days</option>)}
            </select>
          </div>
          <div className="flex flex-wrap gap-3">
            {SCOPES.filter(([s]) => s !== 'observations' || pro?.user_role === 'counselor').map(([s, l]) => (
              <label key={s} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={g.scopes.includes(s)} onChange={(e) => setG({ ...g, scopes: e.target.checked ? [...g.scopes, s] : g.scopes.filter((x) => x !== s) })} />{l}</label>
            ))}
          </div>
          <ErrorNote msg={err} />
          <button className="btn-primary" disabled={!g.grantee_id || !g.scopes.length} onClick={grant}><UserPlus size={15} /> Grant access</button>
        </section>
      )}

      <section className="card p-5">
        <h2 className="text-lg font-semibold">{isInd ? 'Who can see my information' : 'Access granted to you'}</h2>
        <ul className="mt-3 space-y-2">
          {grants?.map((x) => (
            <li key={x.grant_id} className="flex flex-wrap items-center gap-3 rounded-xl bg-surface2 p-3 text-sm">
              <ShieldCheck size={16} className={x.status === 'active' ? 'text-leaf' : 'text-muted'} />
              <div className="flex-1"><b>{isInd ? x.grantee_name : x.user_name}</b> · {x.scopes.join(', ')}<div className="text-xs text-muted">{x.status} · granted {x.granted_at.slice(0, 10)}{x.expires_at ? ` · expires ${x.expires_at.slice(0, 10)}` : ''}{x.revoked_at ? ` · revoked ${x.revoked_at.slice(0, 10)}` : ''}</div></div>
              {isInd && x.status === 'active' && <button className="btn-ghost min-h-[36px] text-xs" onClick={() => revoke(x.grant_id)}><XCircle size={14} /> Revoke</button>}
            </li>
          ))}
          {!grants?.length && <li className="text-sm text-muted">No one has access.</li>}
        </ul>
      </section>

      <section className="card space-y-3 p-5">
        <h2 className="text-lg font-semibold">Your data rights</h2>
        <p className="text-sm text-muted">Under India's Digital Personal Data Protection Act, 2023 you can access, correct and erase your personal data and withdraw consent. Correct your details in My Profile.</p>
        <div className="flex flex-wrap gap-2">
          <button className="btn-ghost" onClick={exportData}><Download size={15} /> Download my data (JSON)</button>
          <button className="btn-ghost" style={{ color: 'var(--lv-attention)' }} onClick={del}><Trash2 size={15} /> Delete my account</button>
        </div>
        <details className="text-sm"><summary className="cursor-pointer font-semibold">Consent history</summary>
          <ul className="mt-2 space-y-1 text-xs text-muted">{consents.history.map((h: any, i: number) => <li key={i}>{h.timestamp.replace('T', ' ').slice(0, 16)} — {h.type}: {h.granted ? 'granted' : 'declined/withdrawn'} (v{h.version})</li>)}</ul>
        </details>
      </section>
    </div>
  )
}
