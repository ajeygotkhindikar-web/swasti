import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { CalendarPlus } from 'lucide-react'
import { api } from '../lib/api'
import { useApi } from '../lib/hooks'
import { useAuth } from '../lib/auth'
import { CategoryIcon, Delta, Empty, ErrorNote, LevelBadge, PageHeader, Spinner } from '../components/ui'
import { fmt } from '../lib/levels'

export default function Reviews() {
  const [sp] = useSearchParams()
  const uid = sp.get('user_id')
  const q = uid ? `?user_id=${uid}` : ''
  const { user } = useAuth()
  const { data, loading, reload, error } = useApi<any[]>(`/reviews${q}`)
  const [err, setErr] = useState<string | null>(null)
  const [sel, setSel] = useState(0)
  const create = async () => { setErr(null); try { await api(`/reviews${q}`, { method: 'POST' }); setSel(0); reload() } catch (e: any) { setErr(e.message) } }
  const saveNotes = async (id: string, coach_notes: string) => { await api(`/reviews/${id}/coach-notes`, { method: 'PATCH', body: { coach_notes } }); reload() }
  if (loading) return <Spinner />
  const r = data?.[sel]
  const isPro = user?.user_role === 'coach' || user?.user_role === 'counselor'
  return (
    <div>
      <PageHeader title="Quarterly Reviews" subtitle="Every three months, the same short questions show what has genuinely changed. Earlier results are always preserved."
        actions={<button className="btn-primary" onClick={create}><CalendarPlus size={16} /> Create review from latest assessment</button>} />
      <ErrorNote msg={err ?? error} />
      {!data?.length ? <Empty title="No reviews yet">Complete an assessment, then create your first review.</Empty> : (
        <>
          <div className="mb-4 flex flex-wrap gap-2">
            {data.map((x, i) => <button key={x.review_id} onClick={() => setSel(i)} className={`btn min-h-[40px] ${i === sel ? 'bg-fill text-onfill border border-fillstrong' : 'btn-ghost'}`}>{x.year} Q{x.quarter}</button>)}
          </div>
          {r && (
            <div className="space-y-4">
              <div className="card p-5">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h2 className="text-xl font-semibold">{r.year} · Quarter {r.quarter}</h2>
                  <span className="text-sm text-muted">Reviewed {r.review_date}{r.coach_name ? ` with ${r.coach_name}` : ''}</span>
                </div>
                <p className="mt-2 text-sm">{r.review_summary}</p>
                {r.overall_progress !== null && <p className="mt-2 text-sm">Average change across dimensions: <Delta value={r.overall_progress} /></p>}
              </div>
              <div className="card overflow-x-auto p-2 sm:p-4">
                <table className="w-full min-w-[640px] text-sm">
                  <thead><tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
                    <th className="p-2">Dimension</th><th className="p-2 text-right">Baseline ({r.comparison.baseline_period})</th><th className="p-2 text-right">Previous</th><th className="p-2 text-right">Current</th><th className="p-2 text-right">Target</th><th className="p-2">Change</th><th className="p-2">Next quarter</th>
                  </tr></thead>
                  <tbody>
                    {r.comparison.rows.map((row: any) => (
                      <tr key={row.category_id} className="border-b border-line/60 align-top">
                        <td className="p-2"><div className="flex items-center gap-2"><CategoryIcon id={row.category_id} size={11} />{row.category_name}</div><div className="mt-1"><LevelBadge level={row.level} small /></div></td>
                        <td className="p-2 text-right tabular-nums">{fmt(row.baseline)}</td><td className="p-2 text-right tabular-nums">{fmt(row.previous)}</td>
                        <td className="p-2 text-right font-semibold tabular-nums">{fmt(row.current)}</td><td className="p-2 text-right tabular-nums">{fmt(row.next_quarter_target ?? row.target)}</td>
                        <td className="p-2"><Delta value={row.change} /></td>
                        <td className="p-2 text-xs text-muted">{row.next_quarter_actions?.join('; ')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="card p-5">
                <h3 className="font-semibold">Coach discussion notes</h3>
                {isPro
                  ? <textarea className="input mt-2 min-h-[100px] py-2" defaultValue={r.coach_notes ?? ''} onBlur={(e) => saveNotes(r.review_id, e.target.value)} placeholder="Agreed actions, reflections…" />
                  : <p className="mt-2 text-sm text-muted">{r.coach_notes ?? 'You can share this review with a coach from Privacy & Consent to discuss your results together.'}</p>}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
