import { useState } from 'react'
import clsx from 'clsx'
import { Check, Pause, Pencil, Play, Plus, Trash2 } from 'lucide-react'
import { api } from '../lib/api'
import { useApi } from '../lib/hooks'
import { CategoryIcon, Empty, ErrorNote, PageHeader, Spinner } from '../components/ui'

export default function Habits() {
  const { data: habits, loading, reload, setData } = useApi<any[]>('/habits')
  const { data: cats } = useApi<any[]>('/categories')
  const [form, setForm] = useState({ category_id: 'MEN', habit_name: '', frequency: 'daily', target_frequency: 1, reminder_time: '' })
  const [show, setShow] = useState(false)
  const [edit, setEdit] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  if (loading || !cats) return <Spinner />
  const name = (id: string) => cats.find((c) => c.category_id === id)?.category_name
  const toggle = async (h: any) => {
    const r = await api(`/habits/${h.habit_id}/log`, { method: h.done_today ? 'DELETE' : 'POST', body: h.done_today ? undefined : {} })
    setData((hs) => hs!.map((x) => (x.habit_id === h.habit_id ? r : x)))
  }
  const patch = async (h: any, body: any) => { await api(`/habits/${h.habit_id}`, { method: 'PATCH', body }); reload() }
  const create = async (e: React.FormEvent) => {
    e.preventDefault(); setErr(null)
    try { await api('/habits', { method: 'POST', body: { ...form, reminder_time: form.reminder_time || null } }); setShow(false); setForm({ ...form, habit_name: '' }); reload() } catch (e: any) { setErr(e.message) }
  }
  return (
    <div>
      <PageHeader title="Micro-Habits" subtitle="Small, achievable actions. Skipping a day is completely fine — consistency over time matters more than streaks."
        actions={<button className="btn-primary" onClick={() => setShow(!show)}><Plus size={16} /> New habit</button>} />
      {show && (
        <form onSubmit={create} className="card mb-6 grid gap-3 p-4 sm:grid-cols-6">
          <div className="sm:col-span-2"><label className="label" htmlFor="hn">Habit</label><input id="hn" className="input" required minLength={2} value={form.habit_name} onChange={(e) => setForm({ ...form, habit_name: e.target.value })} placeholder="e.g. Five minutes of quiet reflection" /></div>
          <div><label className="label" htmlFor="hc">Dimension</label><select id="hc" className="input" value={form.category_id} onChange={(e) => setForm({ ...form, category_id: e.target.value })}>{cats.map((c) => <option key={c.category_id} value={c.category_id}>{c.category_name}</option>)}</select></div>
          <div><label className="label" htmlFor="hf">Frequency</label><select id="hf" className="input" value={form.frequency} onChange={(e) => setForm({ ...form, frequency: e.target.value })}><option value="daily">Daily</option><option value="weekly">Weekly</option></select></div>
          <div><label className="label" htmlFor="hr">Reminder (optional)</label><input id="hr" type="time" className="input" value={form.reminder_time} onChange={(e) => setForm({ ...form, reminder_time: e.target.value })} /></div>
          <div className="flex items-end"><button className="btn-primary w-full">Add</button></div>
          <div className="sm:col-span-6"><ErrorNote msg={err} /></div>
        </form>
      )}
      {!habits?.length ? <Empty title="No habits yet">Add one here, or pick a suggested micro-habit from My Recommendations.</Empty> : (
        <div className="grid gap-3 md:grid-cols-2">
          {habits.map((h) => (
            <div key={h.habit_id} className={clsx('card p-4', h.status === 'paused' && 'opacity-60')}>
              <div className="flex items-start gap-3">
                <button onClick={() => toggle(h)} disabled={h.status !== 'active'} aria-pressed={h.done_today} aria-label={h.done_today ? `Undo ${h.habit_name} today` : `Mark ${h.habit_name} done today`}
                  className={clsx('grid h-12 w-12 shrink-0 place-items-center rounded-2xl border-2 transition', h.done_today ? 'border-leaf bg-leaf text-white' : 'border-line hover:border-leaf')}>
                  <Check size={22} />
                </button>
                <div className="min-w-0 flex-1">
                  {edit === h.habit_id
                    ? <input autoFocus className="input" defaultValue={h.habit_name} onBlur={(e) => { setEdit(null); e.target.value !== h.habit_name && patch(h, { habit_name: e.target.value }) }} />
                    : <div className="font-semibold">{h.habit_name}</div>}
                  <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted"><CategoryIcon id={h.category_id} size={10} framed={false} />{name(h.category_id)} · {h.frequency}{h.reminder_time ? ` · reminder ${h.reminder_time}` : ''} · {h.completion_count} total</div>
                </div>
              </div>
              <div className="mt-3 flex gap-[3px]" aria-label="Last 28 days">
                {h.last_28_days.map((d: boolean, i: number) => <span key={i} className={clsx('h-5 flex-1 rounded-[4px]', d ? 'bg-leaf' : 'bg-surface2')} title={d ? 'done' : ''} />)}
              </div>
              <div className="mt-1 flex justify-between text-[10px] text-muted"><span>4 weeks ago</span><span>today</span></div>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <select aria-label="Frequency" className="input min-h-[36px] w-auto py-0 text-xs" value={h.frequency} onChange={(e) => patch(h, { frequency: e.target.value })}><option value="daily">Daily</option><option value="weekly">Weekly</option></select>
                <button className="btn-ghost min-h-[36px] px-3 text-xs" onClick={() => setEdit(h.habit_id)}><Pencil size={13} /> Rename</button>
                <button className="btn-ghost min-h-[36px] px-3 text-xs" onClick={() => patch(h, { status: h.status === 'active' ? 'paused' : 'active' })}>{h.status === 'active' ? <><Pause size={13} /> Pause</> : <><Play size={13} /> Resume</>}</button>
                <button className="btn-ghost min-h-[36px] px-3 text-xs" onClick={() => patch(h, { status: 'archived' })}><Trash2 size={13} /> Archive</button>
              </div>
              <input className="input mt-2 min-h-[36px] text-xs" placeholder="Feedback — too hard? too easy? (optional)" defaultValue={h.user_feedback ?? ''} onBlur={(e) => e.target.value !== (h.user_feedback ?? '') && patch(h, { user_feedback: e.target.value })} />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
