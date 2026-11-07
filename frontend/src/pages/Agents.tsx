import { useState } from 'react'
import { Bot, Play, ShieldCheck } from 'lucide-react'
import { api } from '../lib/api'
import { useApi } from '../lib/hooks'
import { useAuth } from '../lib/auth'
import { CategoryIcon, ErrorNote, PageHeader, Spinner } from '../components/ui'

export default function Agents() {
  const { user } = useAuth()
  const { data: agents, loading } = useApi<any[]>('/agents')
  const isInd = user?.user_role === 'individual'
  const { data: dash } = useApi<any>(isInd ? '/dashboard' : null)
  const aid = dash?.overview?.latest_assessment_id
  const { data: logs, reload: reloadLogs } = useApi<any[]>(aid ? `/assessments/${aid}/agent-logs` : null, [aid])
  const [busy, setBusy] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const runAll = async () => {
    setBusy('all'); setErr(null)
    try { const r = await api(`/assessments/${aid}/agents/run`, { method: 'POST', body: { background: false, parallel: true } }); setMsg(`Run ${r.run_id.slice(0, 8)}: ${r.status} · ${r.insights} cross-insights`); reloadLogs() }
    catch (e: any) { setErr(e.message) } finally { setBusy(null) }
  }
  const runOne = async (id: string) => {
    setBusy(id); setErr(null)
    try { const r = await api(`/agents/${id}/run?assessment_id=${aid}`, { method: 'POST' }); setMsg(`${id}: score ${r.current_score ?? '—'} (${r.current_level})`); reloadLogs() }
    catch (e: any) { setErr(e.message) } finally { setBusy(null) }
  }
  if (loading) return <Spinner />
  const last = (id: string) => logs?.find((l) => l.agent_id === id)
  return (
    <div>
      <PageHeader title="Wellness AI Agents" subtitle="Fourteen specialised agents, one per dimension. Each runs independently (in parallel under a central orchestrator), uses only the curated, referenced knowledge base, and never diagnoses, prescribes or recommends financial products."
        actions={isInd && aid ? <button className="btn-primary" onClick={runAll} disabled={!!busy}><Play size={15} /> {busy === 'all' ? 'Running 14 agents…' : 'Re-run all agents'}</button> : undefined} />
      {msg && <p className="mb-4 rounded-xl bg-teal-soft p-3 text-sm text-teal">{msg}</p>}
      <ErrorNote msg={err} />
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {agents?.map((a) => {
          const l = last(a.agent_id)
          return (
            <div key={a.agent_id} className="card flex flex-col gap-3 p-4">
              <div className="flex items-center gap-3">
                <CategoryIcon id={a.category_id} size={16} />
                <div className="flex-1"><div className="text-sm font-semibold">{a.agent_name}</div><div className="text-xs text-muted">{a.agent_id} · v{a.version} · {a.execution_mode}</div></div>
                <span className={`chip border ${a.status === 'active' ? 'border-leaf text-leaf' : 'border-line text-muted'}`}><Bot size={11} /> {a.status}</span>
              </div>
              <p className="text-sm text-muted">{a.description}</p>
              <p className="flex gap-1.5 text-xs text-muted"><ShieldCheck size={13} className="shrink-0 text-teal" />{a.guardrail}</p>
              {isInd && aid && (
                <div className="mt-auto flex items-center justify-between border-t border-line pt-3 text-xs text-muted">
                  <span>{l ? `Last run: ${l.status}, attempt ${l.attempt}, ${l.duration_ms} ms` : 'Not yet run'}</span>
                  <button className="btn-ghost min-h-[36px] px-3 text-xs" disabled={!!busy || a.status !== 'active'} onClick={() => runOne(a.agent_id)}>{busy === a.agent_id ? 'Running…' : 'Run this agent'}</button>
                </div>
              )}
            </div>
          )
        })}
      </div>
      <section className="card mt-8 p-5 text-sm">
        <h2 className="text-lg font-semibold">How the agents work</h2>
        <ol className="mt-3 list-decimal space-y-1 pl-5 text-muted">
          <li>Fetch your latest responses for the dimension, plus your history.</li>
          <li>Recalculate the score with the transparent scoring engine; identify strengths (≥75) and growth areas (≤50) item by item.</li>
          <li>Compare against the configurable benchmark and set an achievable next-quarter target (at most +10 points).</li>
          <li>Select actions from the curated knowledge base, prioritising those addressing your lowest items; each links to a referenced source.</li>
          <li>Save a structured result. The orchestrator retries failures (up to 3×), logs each attempt, and then looks for patterns across dimensions without double-counting or assuming cause.</li>
        </ol>
      </section>
    </div>
  )
}
