import { Link, useParams, useSearchParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { useApi } from '../lib/hooks'
import { useAuth } from '../lib/auth'
import { AgentOutput } from '../components/AgentOutput'
import { CategoryIcon, Empty, ErrorNote, PageHeader, Spinner } from '../components/ui'

export default function CategoryDetail() {
  const { categoryId } = useParams()
  const [sp] = useSearchParams()
  const uid = sp.get('user_id')
  const q = uid ? `?user_id=${uid}` : ''
  const { user } = useAuth()
  const { data: dash, error } = useApi<any>(`/dashboard${q}`)
  const aid = dash?.overview?.latest_assessment_id
  const { data: agents } = useApi<any>(aid ? `/assessments/${aid}/agents` : null, [aid])
  const { data: detail } = useApi<any>(aid ? `/assessments/${aid}` : null, [aid])
  const { data: cats } = useApi<any[]>('/categories')
  if (error) return <ErrorNote msg={error} />
  if (!dash || !cats) return <Spinner />
  const cat = cats.find((c) => c.category_id === categoryId)
  const out = agents?.results?.find((r: any) => r.category_id === categoryId)
  const resp = Object.fromEntries((detail?.responses ?? []).map((r: any) => [r.parameter_id, r]))
  return (
    <div className="space-y-6">
      <Link to={`/dashboard${q}`} className="inline-flex items-center gap-1 text-sm font-semibold text-teal"><ArrowLeft size={15} /> Dashboard</Link>
      <div className="flex items-center gap-3"><CategoryIcon id={categoryId} size={22} /><PageHeader title={cat?.category_name ?? ''} subtitle={cat?.description} /></div>
      <div className="grid gap-6 lg:grid-cols-3">
        <section className="card p-5 lg:col-span-2">
          <h2 className="mb-4 text-lg font-semibold">{out ? `${out.agent_id.replace('_', ' ')} analysis` : 'Agent analysis'}</h2>
          {out ? <AgentOutput out={out} canPlan={user?.user_role === 'individual' && !uid} /> : <Empty title="Analysis in progress">The agent hasn't finished yet — refresh in a moment.</Empty>}
        </section>
        <section className="card p-5">
          <h2 className="mb-3 text-lg font-semibold">Your answers</h2>
          <ul className="space-y-3 text-sm">
            {cat?.parameters.map((p: any) => {
              const r = resp[p.parameter_id]
              const label = r?.status === 'answered' ? p.options.find((o: any) => o.value === r.value)?.label : r?.status?.replaceAll('_', ' ')
              return (
                <li key={p.parameter_id}>
                  <div className="text-muted">{p.question}</div>
                  <div className="mt-0.5 flex justify-between font-semibold"><span className="capitalize">{label ?? 'Not answered'}</span>{r?.normalized_score != null && <span className="tabular-nums">{Math.round(r.normalized_score)}/100{p.reverse ? ' (reverse-scored)' : ''}</span>}</div>
                </li>
              )
            })}
          </ul>
          {detail?.category_comments?.[categoryId!] && <p className="mt-4 rounded-xl bg-surface2 p-3 text-sm">“{detail.category_comments[categoryId!]}”</p>}
          <p className="mt-4 text-xs text-muted">Each answer maps to 0–100: (value − 1) ÷ 4 × 100, reversed where a higher frequency is less healthy (e.g. stress). Skipped or “not applicable” answers are excluded, never counted as zero.</p>
        </section>
      </div>
    </div>
  )
}
