import { useState } from 'react'
import clsx from 'clsx'
import { api } from '../lib/api'
import { useApi } from '../lib/hooks'
import { AgentOutput, EvidenceLink } from '../components/AgentOutput'
import { CategoryIcon, Empty, LevelBadge, PageHeader, Spinner } from '../components/ui'
import { fmt } from '../lib/levels'

export default function Recommendations() {
  const { data: dash } = useApi<any>('/dashboard')
  const aid = dash?.overview?.latest_assessment_id
  const { data: agents } = useApi<any>(aid ? `/assessments/${aid}/agents` : null, [aid])
  const { data: plans, reload } = useApi<any[]>('/plans')
  const { data: kb } = useApi<any[]>('/recommendations')
  const [tab, setTab] = useState<'mine' | 'plan' | 'kb'>('mine')
  const [open, setOpen] = useState<string | null>(null)
  if (!dash) return <Spinner />
  const results = [...(agents?.results ?? [])].sort((a, b) => (a.current_score ?? 101) - (b.current_score ?? 101))
  const setPlan = async (id: string, body: any) => { await api(`/plans/${id}`, { method: 'PATCH', body }); reload() }
  return (
    <div>
      <PageHeader title="My Recommendations" subtitle="Personalised by your 14 agents, ordered by where you have the most room to grow. Every action links to a referenced source." />
      <div className="mb-5 flex gap-2" role="tablist">
        {([['mine', 'For me'], ['plan', `My plan (${plans?.filter((p) => p.completion_status === 'active').length ?? 0})`], ['kb', 'Knowledge base']] as const).map(([k, l]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)} className={clsx('btn min-h-[40px]', tab === k ? 'bg-fill text-onfill border border-fillstrong' : 'btn-ghost')}>{l}</button>
        ))}
      </div>
      {tab === 'mine' && (!results.length ? <Empty title="No recommendations yet">Complete an assessment to receive personalised recommendations.</Empty> :
        <div className="space-y-3">
          {results.map((r) => (
            <div key={r.category_id} className="card">
              <button className="flex w-full items-center gap-3 p-4 text-left" aria-expanded={open === r.category_id} onClick={() => setOpen(open === r.category_id ? null : r.category_id)}>
                <CategoryIcon id={r.category_id} size={16} />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2 text-sm font-semibold">{dash.cards.find((c: any) => c.category_id === r.category_id)?.category_name}<LevelBadge level={r.current_level} small /></div>
                  <div className="truncate text-xs text-muted">{r.recommended_actions.map((a: any) => a.title).join(' · ')}</div>
                </div>
                <span className="text-sm font-semibold tabular-nums">{fmt(r.current_score)} → {fmt(r.target_score)}</span>
              </button>
              {open === r.category_id && <div className="border-t border-line p-4"><AgentOutput out={r} canPlan /></div>}
            </div>
          ))}
        </div>)}
      {tab === 'plan' && (!plans?.length ? <Empty title="Your plan is empty">Add a recommendation from "For me" to build your next-quarter plan.</Empty> :
        <div className="grid gap-3 md:grid-cols-2">
          {plans.map((p) => (
            <div key={p.plan_id} className="card space-y-2 p-4">
              <div className="flex items-center gap-2"><CategoryIcon id={p.category_id} size={14} /><b className="text-sm">{p.title}</b><span className="chip ml-auto border border-line text-muted">{p.completion_status}</span></div>
              <p className="text-sm">{p.action}</p>
              <p className="text-xs text-muted">Micro-habit: {p.micro_habit} · target {p.target_date}</p>
              <textarea className="input min-h-[60px] py-2 text-xs" placeholder="How is it going? (optional feedback)" defaultValue={p.user_feedback ?? ''} onBlur={(e) => e.target.value !== (p.user_feedback ?? '') && setPlan(p.plan_id, { user_feedback: e.target.value })} />
              <div className="flex gap-2">
                {p.completion_status !== 'completed' && <button className="btn-ghost min-h-[36px] text-xs" onClick={() => setPlan(p.plan_id, { completion_status: 'completed' })}>Mark done</button>}
                {p.completion_status === 'active' && <button className="btn-ghost min-h-[36px] text-xs" onClick={() => setPlan(p.plan_id, { completion_status: 'dropped' })}>Not for me</button>}
                {p.completion_status !== 'active' && <button className="btn-ghost min-h-[36px] text-xs" onClick={() => setPlan(p.plan_id, { completion_status: 'active' })}>Reactivate</button>}
              </div>
            </div>
          ))}
        </div>)}
      {tab === 'kb' && (
        <div className="grid gap-3 md:grid-cols-2">
          {kb?.map((r) => (
            <div key={r.recommendation_id} className="card space-y-2 p-4">
              <div className="flex items-center gap-2"><CategoryIcon id={r.category_id} size={14} /><b className="text-sm">{r.title}</b><span className="ml-auto text-[11px] text-muted">{r.recommendation_id}</span></div>
              <p className="text-sm">{r.action}</p>
              <p className="text-xs text-muted">{r.description}</p>
              {r.evidence && <EvidenceLink e={r.evidence} />}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
