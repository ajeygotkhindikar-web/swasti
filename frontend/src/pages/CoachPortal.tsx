import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, CalendarClock, LayoutDashboard, Mic, NotebookPen } from 'lucide-react'
import { api } from '../lib/api'
import { useApi } from '../lib/hooks'
import { useAuth } from '../lib/auth'
import { Empty, ErrorNote, PageHeader, Spinner } from '../components/ui'
import { fmt } from '../lib/levels'

function ClientCard({ c, isCounselor }: { c: any; isCounselor: boolean }) {
  const [open, setOpen] = useState<'none' | 'schedule' | 'observe'>('none')
  const { data: interviews, reload } = useApi<any[]>(c.scopes.includes('interviews') ? `/interviews?user_id=${c.user_id}` : null)
  const { data: observations, reload: reloadObs } = useApi<any[]>(isCounselor && c.scopes.includes('observations') ? `/counselor/observations?user_id=${c.user_id}` : null)
  const [when, setWhen] = useState('')
  const [obs, setObs] = useState({ observation: '', referral_recommended: false, referral_note: '', follow_up_date: '' })
  const [err, setErr] = useState<string | null>(null)
  const schedule = async () => { setErr(null); try { await api('/interviews/schedule', { method: 'POST', body: { user_id: c.user_id, scheduled_for: new Date(when).toISOString() } }); setOpen('none'); reload() } catch (e: any) { setErr(e.message) } }
  const observe = async () => { setErr(null); try { await api('/counselor/observations', { method: 'POST', body: { user_id: c.user_id, ...obs, referral_note: obs.referral_note || null, follow_up_date: obs.follow_up_date || null } }); setOpen('none'); reloadObs() } catch (e: any) { setErr(e.message) } }
  const ov = c.overview
  return (
    <div className="card space-y-4 p-5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div><h2 className="font-sans text-base font-semibold">{c.full_name}</h2><p className="text-xs text-muted">{[c.occupation, c.city].filter(Boolean).join(' · ')} · access: {c.scopes.join(', ')}</p></div>
        {ov && <div className="text-right text-sm"><span className="font-display text-2xl font-semibold">{fmt(ov.overall_indicator)}</span><div className="text-xs text-muted">{ov.dimensions_assessed}/14 assessed · last {ov.last_assessment_date ?? '—'}</div></div>}
      </div>
      {c.attention_flags?.length > 0 && <p className="flex gap-2 text-sm"><AlertTriangle size={15} className="mt-0.5 shrink-0" style={{ color: 'var(--lv-attention)' }} />Wellness gaps: {c.attention_flags.map((f: any) => `${f.category_name} (${fmt(f.score)})`).join(', ')}</p>}
      <div className="flex flex-wrap gap-2 text-xs text-muted">
        <span>Last interview: {c.last_interview?.slice(0, 10) ?? '—'}</span><span>· Next follow-up: {c.next_follow_up ?? '—'}</span>
        {ov?.review_due && <span className="chip border border-saffron text-saffron">Quarterly review due</span>}
      </div>
      <div className="flex flex-wrap gap-2">
        {c.scopes.includes('assessments') && <Link className="btn-ghost min-h-[38px] text-xs" to={`/dashboard?user_id=${c.user_id}`}><LayoutDashboard size={14} /> Dashboard</Link>}
        {c.scopes.includes('assessments') && <Link className="btn-ghost min-h-[38px] text-xs" to={`/reviews?user_id=${c.user_id}`}>Quarterly comparison</Link>}
        {c.scopes.includes('interviews') && <Link className="btn-ghost min-h-[38px] text-xs" to={`/interview?user_id=${c.user_id}`}><Mic size={14} /> Interview</Link>}
        {c.scopes.includes('interviews') && <button className="btn-ghost min-h-[38px] text-xs" onClick={() => setOpen(open === 'schedule' ? 'none' : 'schedule')}><CalendarClock size={14} /> Schedule</button>}
        {isCounselor && c.scopes.includes('observations') && <button className="btn-ghost min-h-[38px] text-xs" onClick={() => setOpen(open === 'observe' ? 'none' : 'observe')}><NotebookPen size={14} /> Professional note</button>}
      </div>
      {open === 'schedule' && <div className="flex flex-wrap gap-2"><input type="datetime-local" className="input w-auto" value={when} onChange={(e) => setWhen(e.target.value)} /><button className="btn-primary" disabled={!when} onClick={schedule}>Schedule</button></div>}
      {open === 'observe' && (
        <div className="space-y-2">
          <textarea className="input min-h-[80px] py-2" placeholder="Professional observation" value={obs.observation} onChange={(e) => setObs({ ...obs, observation: e.target.value })} />
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={obs.referral_recommended} onChange={(e) => setObs({ ...obs, referral_recommended: e.target.checked })} /> Referral recommended</label>
          {obs.referral_recommended && <input className="input" placeholder="Referral note" value={obs.referral_note} onChange={(e) => setObs({ ...obs, referral_note: e.target.value })} />}
          <input type="date" className="input w-auto" value={obs.follow_up_date} onChange={(e) => setObs({ ...obs, follow_up_date: e.target.value })} aria-label="Follow-up date" />
          <button className="btn-primary" disabled={obs.observation.length < 2} onClick={observe}>Save note</button>
        </div>
      )}
      <ErrorNote msg={err} />
      {interviews && interviews.length > 0 && (
        <details className="text-sm"><summary className="cursor-pointer font-semibold">Interview history ({interviews.length})</summary>
          <ul className="mt-2 space-y-2">{interviews.map((iv) => <li key={iv.interview_id} className="rounded-xl bg-surface2 p-3"><b>{iv.interview_date.slice(0, 10)}</b> · {iv.status}{iv.interview_summary ? ` — ${iv.interview_summary}` : ''}{iv.follow_up_plan ? <div className="text-xs text-muted">Follow-up: {iv.follow_up_plan} ({iv.follow_up_date ?? 'TBD'})</div> : null}</li>)}</ul>
        </details>
      )}
      {observations && observations.length > 0 && (
        <details className="text-sm"><summary className="cursor-pointer font-semibold">Professional observations ({observations.length})</summary>
          <ul className="mt-2 space-y-2">{observations.map((o) => <li key={o.observation_id} className="rounded-xl bg-surface2 p-3">{o.observation}{o.referral_recommended && <div className="text-xs text-saffron">Referral recommended{o.referral_note ? `: ${o.referral_note}` : ''}</div>}</li>)}</ul>
        </details>
      )}
    </div>
  )
}

export default function CoachPortal() {
  const { user } = useAuth()
  const { data, loading, error } = useApi<any[]>('/coach/clients')
  if (loading) return <Spinner />
  return (
    <div>
      <PageHeader title={user?.user_role === 'counselor' ? 'Counsellor Portal' : 'Coach Portal'} subtitle="Only individuals who have explicitly approved your access appear here. Access ends as soon as they revoke it, and every view is audit-logged." />
      <ErrorNote msg={error} />
      {!data?.length ? <Empty title="No clients yet">When an individual grants you access from their Privacy & Consent page, they'll appear here.</Empty>
        : <div className="grid gap-4 lg:grid-cols-2">{data.map((c) => <ClientCard key={c.user_id} c={c} isCounselor={user?.user_role === 'counselor'} />)}</div>}
    </div>
  )
}
