import { useState } from 'react'
import clsx from 'clsx'
import { CheckCircle2, ExternalLink, ShieldCheck } from 'lucide-react'
import { api } from '../lib/api'
import { useApi } from '../lib/hooks'
import { CategoryIcon, ErrorNote, PageHeader, Spinner, Stat } from '../components/ui'
import { fmt } from '../lib/levels'

const TABS = ['Overview', 'Categories', 'Scoring', 'Evidence', 'Agents', 'Users', 'Analytics', 'Audit'] as const

function Overview() {
  const { data } = useApi<any>('/admin/system')
  if (!data) return <Spinner />
  const agents = Object.entries(data.agent_stats) as [string, any][]
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Active users" value={data.users} /><Stat label="Assessments" value={data.assessments} /><Stat label="Active access grants" value={data.active_grants} />
        <Stat label="Agent success" value={`${agents.reduce((n, [, s]) => n + s.succeeded, 0)} / ${agents.reduce((n, [, s]) => n + s.succeeded + s.failed, 0)}`} hint="executions" />
      </div>
      <div className="card overflow-x-auto p-4">
        <table className="w-full text-sm"><thead><tr className="text-left text-xs uppercase text-muted"><th className="p-2">Agent</th><th className="p-2 text-right">Succeeded</th><th className="p-2 text-right">Failed attempts</th><th className="p-2 text-right">Avg ms</th></tr></thead>
          <tbody>{agents.map(([id, s]) => <tr key={id} className="border-t border-line"><td className="p-2">{id}</td><td className="p-2 text-right">{s.succeeded}</td><td className="p-2 text-right">{s.failed}</td><td className="p-2 text-right">{s.avg_ms ?? '—'}</td></tr>)}</tbody></table>
      </div>
      <button className="btn-ghost" onClick={() => api('/admin/notifications/run', { method: 'POST' }).then((r) => alert(`Reminder engine processed ${r.processed_users} users`))}>Run reminder engine now</button>
    </div>
  )
}

function Categories() {
  const { data, reload } = useApi<any[]>('/admin/categories')
  const [open, setOpen] = useState<string | null>(null)
  if (!data) return <Spinner />
  const patchC = async (id: string, body: any) => { await api(`/admin/categories/${id}`, { method: 'PATCH', body }); reload() }
  const patchP = async (id: string, body: any) => { await api(`/admin/parameters/${id}`, { method: 'PATCH', body }); reload() }
  return (
    <div className="space-y-2">
      {data.map((c) => (
        <div key={c.category_id} className="card">
          <div className="flex flex-wrap items-center gap-3 p-3">
            <CategoryIcon id={c.category_id} size={14} />
            <button className="flex-1 text-left text-sm font-semibold" onClick={() => setOpen(open === c.category_id ? null : c.category_id)}>{c.category_name} <span className="text-xs text-muted">({c.parameters.length} questions)</span></button>
            <label className="text-xs text-muted">Weight <input type="number" step="0.1" min="0" max="5" className="input ml-1 inline w-20 min-h-[36px]" defaultValue={c.weightage} onBlur={(e) => +e.target.value !== c.weightage && patchC(c.category_id, { default_weightage: +e.target.value })} /></label>
            <label className="text-xs text-muted">Target <input type="number" min="0" max="100" className="input ml-1 inline w-20 min-h-[36px]" defaultValue={c.target_score} onBlur={(e) => +e.target.value !== c.target_score && patchC(c.category_id, { target_score: +e.target.value })} /></label>
            <label className="flex items-center gap-1 text-xs"><input type="checkbox" checked={c.is_active} onChange={(e) => patchC(c.category_id, { is_active: e.target.checked })} /> Active</label>
          </div>
          {open === c.category_id && (
            <div className="border-t border-line p-3">
              {c.parameters.map((p: any) => (
                <div key={p.parameter_id} className="grid gap-2 border-b border-line/60 py-2 text-sm sm:grid-cols-[6rem_1fr_auto]">
                  <span className="text-xs text-muted">{p.parameter_id}<br />{p.response_type}{p.reverse ? ' · reversed' : ''}</span>
                  <textarea className="input min-h-[44px] py-2 text-sm" defaultValue={p.question} onBlur={(e) => e.target.value !== p.question && patchP(p.parameter_id, { parameter_description: e.target.value })} />
                  <div className="flex items-center gap-2 text-xs">
                    <label>Weight <input type="number" step="0.1" min="0.1" max="5" className="input inline w-16 min-h-[36px]" defaultValue={p.weightage} onBlur={(e) => +e.target.value !== p.weightage && patchP(p.parameter_id, { parameter_weightage: +e.target.value })} /></label>
                    <label className="flex items-center gap-1"><input type="checkbox" checked={p.allow_not_applicable} onChange={(e) => patchP(p.parameter_id, { allow_not_applicable: e.target.checked })} />N/A</label>
                    <label className="flex items-center gap-1"><input type="checkbox" checked={p.is_active} onChange={(e) => patchP(p.parameter_id, { is_active: e.target.checked })} />Active</label>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function Scoring() {
  const { data, reload } = useApi<any>('/admin/settings')
  const [levels, setLevels] = useState<string>('')
  const [cfg, setCfg] = useState<string>('')
  const [msg, setMsg] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  if (!data) return <Spinner />
  const save = async (key: string, text: string) => {
    setErr(null); setMsg(null)
    try { await api(`/admin/settings/${key}`, { method: 'PUT', body: { value: JSON.parse(text) } }); setMsg('Saved. New assessments and agent runs use the updated configuration.'); reload() } catch (e: any) { setErr(e.message) }
  }
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="card space-y-2 p-4">
        <h3 className="font-semibold">Wellness level bands</h3>
        <p className="text-xs text-muted">{data.wellness_levels.description} Bands must cover 0–100 in order. Validate changes with qualified domain experts.</p>
        <textarea className="input min-h-[260px] py-2 font-mono text-xs" defaultValue={JSON.stringify(data.wellness_levels.value, null, 2)} onChange={(e) => setLevels(e.target.value)} />
        <button className="btn-primary" disabled={!levels} onClick={() => save('wellness_levels', levels)}>Save bands</button>
      </div>
      <div className="card space-y-2 p-4">
        <h3 className="font-semibold">Scoring engine</h3>
        <ul className="text-xs text-muted">
          <li><b>min_category_coverage</b>: share of a dimension's questions that must be answered to score it.</li>
          <li><b>min_categories_for_overall</b>: dimensions needed before showing an overall indicator.</li>
          <li><b>quarterly_step</b>: maximum improvement used for achievable targets.</li>
        </ul>
        <textarea className="input min-h-[160px] py-2 font-mono text-xs" defaultValue={JSON.stringify(data.scoring_config.value, null, 2)} onChange={(e) => setCfg(e.target.value)} />
        <button className="btn-primary" disabled={!cfg} onClick={() => save('scoring_config', cfg)}>Save configuration</button>
      </div>
      <div className="lg:col-span-2">{msg && <p className="text-sm text-leaf">{msg}</p>}<ErrorNote msg={err} /></div>
    </div>
  )
}

function Evidence() {
  const { data, reload } = useApi<any[]>('/references')
  if (!data) return <Spinner />
  const verify = async (id: string, v: boolean) => { await api(`/admin/references/${id}?verified=${v}`, { method: 'PATCH' }); reload() }
  return (
    <div className="space-y-2">
      <p className="text-sm text-muted">Every recommendation is linked to one of these sources. Seeded links are marked <b>pending verification</b> — open each, confirm it is current and supports the linked guidance, then mark it verified.</p>
      {data.map((r) => (
        <div key={r.reference_id} className="card flex flex-wrap items-center gap-3 p-3 text-sm">
          <span className="w-24 text-xs text-muted">{r.reference_id}</span>
          <div className="min-w-0 flex-1"><a className="font-semibold text-teal hover:underline" href={r.url} target="_blank" rel="noreferrer">{r.title} <ExternalLink size={12} className="inline" /></a><div className="text-xs text-muted">{r.organization} · {r.evidence_level}{r.publication_date ? ` · ${r.publication_date}` : ''}</div></div>
          {r.verification_status === 'verified'
            ? <span className="chip border border-leaf text-leaf"><CheckCircle2 size={12} /> verified {r.last_verified_date}</span>
            : <button className="btn-ghost min-h-[36px] text-xs" onClick={() => verify(r.reference_id, true)}><ShieldCheck size={13} /> Mark verified</button>}
          {r.verification_status === 'verified' && <button className="text-xs text-muted underline" onClick={() => verify(r.reference_id, false)}>flag for review</button>}
        </div>
      ))}
    </div>
  )
}

function Agents() {
  const { data, reload } = useApi<any[]>('/agents')
  if (!data) return <Spinner />
  const patch = async (id: string, body: any) => { await api(`/admin/agents/${id}`, { method: 'PATCH', body }); reload() }
  return (
    <div className="card overflow-x-auto p-2">
      <table className="w-full text-sm"><thead><tr className="text-left text-xs uppercase text-muted"><th className="p-2">Agent</th><th className="p-2">Version</th><th className="p-2">Mode</th><th className="p-2">Status</th></tr></thead>
        <tbody>{data.map((a) => (
          <tr key={a.agent_id} className="border-t border-line"><td className="p-2"><div className="flex items-center gap-2"><CategoryIcon id={a.category_id} size={11} />{a.agent_name}</div></td><td className="p-2">{a.version}</td>
            <td className="p-2"><select className="input min-h-[36px] w-auto py-0 text-xs" value={a.execution_mode} onChange={(e) => patch(a.agent_id, { execution_mode: e.target.value })}><option>parallel</option><option>sequential</option></select></td>
            <td className="p-2"><select className="input min-h-[36px] w-auto py-0 text-xs" value={a.status} onChange={(e) => patch(a.agent_id, { status: e.target.value })}><option>active</option><option>disabled</option></select></td></tr>
        ))}</tbody></table>
    </div>
  )
}

function Users() {
  const { data, reload } = useApi<any[]>('/admin/users')
  const [f, setF] = useState({ full_name: '', email: '', password: '', user_role: 'coach' })
  const [err, setErr] = useState<string | null>(null)
  if (!data) return <Spinner />
  const patch = async (id: string, body: any) => { setErr(null); try { await api(`/admin/users/${id}`, { method: 'PATCH', body }); reload() } catch (e: any) { setErr(e.message) } }
  const create = async (e: React.FormEvent) => { e.preventDefault(); setErr(null); try { await api('/admin/users', { method: 'POST', body: f }); setF({ ...f, full_name: '', email: '', password: '' }); reload() } catch (e: any) { setErr(e.message) } }
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">User management deliberately shows no wellness information. Administrators cannot open individual dashboards.</p>
      <form onSubmit={create} className="card grid gap-2 p-3 sm:grid-cols-5">
        <input className="input" placeholder="Full name" required value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} />
        <input className="input" placeholder="Email" type="email" required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />
        <input className="input" placeholder="Temporary password" type="password" minLength={8} required value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} />
        <select className="input" value={f.user_role} onChange={(e) => setF({ ...f, user_role: e.target.value })}><option value="coach">Coach</option><option value="counselor">Counsellor</option><option value="admin">Admin</option><option value="individual">Individual</option></select>
        <button className="btn-primary">Create user</button>
      </form>
      <ErrorNote msg={err} />
      <div className="card overflow-x-auto p-2">
        <table className="w-full min-w-[640px] text-sm"><thead><tr className="text-left text-xs uppercase text-muted"><th className="p-2">Name</th><th className="p-2">Email</th><th className="p-2">Role</th><th className="p-2">Status</th><th className="p-2">Registered</th></tr></thead>
          <tbody>{data.map((u) => (
            <tr key={u.user_id} className="border-t border-line"><td className="p-2">{u.full_name}</td><td className="p-2 text-muted">{u.email}</td>
              <td className="p-2"><select className="input min-h-[34px] w-auto py-0 text-xs" value={u.user_role} onChange={(e) => patch(u.user_id, { user_role: e.target.value })}><option value="individual">individual</option><option value="coach">coach</option><option value="counselor">counsellor</option><option value="admin">admin</option></select></td>
              <td className="p-2"><select className="input min-h-[34px] w-auto py-0 text-xs" value={u.account_status} onChange={(e) => patch(u.user_id, { account_status: e.target.value })}><option>active</option><option>suspended</option></select></td>
              <td className="p-2 text-muted">{u.registration_date}</td></tr>
          ))}</tbody></table>
      </div>
    </div>
  )
}

function Analytics() {
  const [g, setG] = useState('industry')
  const { data } = useApi<any>(`/admin/analytics?group_by=${g}`, [g])
  const { data: cats } = useApi<any[]>('/categories')
  if (!data || !cats) return <Spinner />
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm">Group by</span>
        {['industry', 'age_group', 'city', 'occupation'].map((x) => <button key={x} onClick={() => setG(x)} className={clsx('chip min-h-[32px] border', g === x ? 'border-teal bg-teal-soft text-teal' : 'border-line')}>{x.replace('_', ' ')}</button>)}
      </div>
      <p className="text-sm text-muted">Anonymised averages of each person's latest assessment. Groups with fewer than <b>{data.min_group_size}</b> people are suppressed ({data.suppressed_groups} hidden).</p>
      <div className="card overflow-x-auto p-2">
        <table className="w-full min-w-[900px] text-xs"><thead><tr className="text-left uppercase text-muted"><th className="p-2">Group</th><th className="p-2">People</th>{cats.map((c) => <th key={c.category_id} className="p-1 text-center" title={c.category_name}><CategoryIcon id={c.category_id} size={10} framed={false} /></th>)}</tr></thead>
          <tbody>{data.groups.map((r: any) => (
            <tr key={r.group} className="border-t border-line"><td className="p-2 font-semibold">{r.group}</td><td className="p-2">{r.people}</td>{cats.map((c) => <td key={c.category_id} className="p-1 text-center tabular-nums">{fmt(r.averages[c.category_id])}</td>)}</tr>
          ))}</tbody></table>
        {data.groups.length === 0 && <p className="p-4 text-sm text-muted">No group meets the minimum size yet.</p>}
      </div>
    </div>
  )
}

function Audit() {
  const { data } = useApi<any[]>('/admin/audit-logs?limit=150')
  if (!data) return <Spinner />
  return (
    <div className="card overflow-x-auto p-2">
      <table className="w-full min-w-[640px] text-xs"><thead><tr className="text-left uppercase text-muted"><th className="p-2">When</th><th className="p-2">Action</th><th className="p-2">Actor</th><th className="p-2">Subject</th><th className="p-2">Resource</th></tr></thead>
        <tbody>{data.map((a) => <tr key={a.audit_id} className="border-t border-line"><td className="p-2">{a.created_at.replace('T', ' ').slice(0, 19)}</td><td className="p-2 font-semibold">{a.action}</td><td className="p-2 text-muted">{a.actor_id?.slice(0, 8)}</td><td className="p-2 text-muted">{a.subject_user_id?.slice(0, 8)}</td><td className="p-2 text-muted">{a.resource}</td></tr>)}</tbody></table>
    </div>
  )
}

export default function Admin() {
  const [tab, setTab] = useState<(typeof TABS)[number]>('Overview')
  const Body = { Overview, Categories, Scoring, Evidence, Agents, Users, Analytics, Audit }[tab]
  return (
    <div>
      <PageHeader title="Administration" subtitle="Configure dimensions, scoring, evidence and agents; manage users; view anonymised analytics. Individual wellness data is never visible here." />
      <div className="mb-5 flex gap-2 overflow-x-auto pb-1" role="tablist">
        {TABS.map((t) => <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)} className={clsx('btn min-h-[40px] shrink-0', tab === t ? 'bg-teal text-onteal' : 'btn-ghost')}>{t}</button>)}
      </div>
      <Body />
    </div>
  )
}
