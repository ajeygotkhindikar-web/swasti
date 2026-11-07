import { Link } from 'react-router-dom'
import { ArrowRight, ClipboardList, LayoutDashboard, Mic, Repeat, Settings, Stethoscope } from 'lucide-react'
import { useAuth } from '../lib/auth'
import { useApi } from '../lib/hooks'
import { CategoryIcon, Disclaimer, LevelBadge, Spinner } from '../components/ui'
import { fmt } from '../lib/levels'

const ASPIRATIONS = ['Balanced Professionals', 'Healthy Families', 'Compassionate Communities', 'A Sustainable Society']

export default function Home() {
  const { user } = useAuth()
  const isInd = user!.user_role === 'individual'
  const { data: dash, loading } = useApi<any>(isInd ? '/dashboard' : null)
  const { data: habits } = useApi<any[]>(isInd ? '/habits' : null)
  const { data: cats } = useApi<any[]>('/categories')
  const hour = new Date().getHours()
  const greet = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

  return (
    <div className="space-y-8">
      <section className="card relative overflow-hidden p-6 sm:p-8">
        <div className="absolute -right-10 -top-10 h-48 w-48 rounded-full bg-saffron-soft" aria-hidden />
        <div className="absolute -right-2 top-20 h-28 w-28 rounded-full bg-teal-soft" aria-hidden />
        <div className="relative">
          <p className="text-sm font-semibold text-saffron">{greet},</p>
          <h1 className="mt-1 text-3xl font-semibold sm:text-4xl">{user!.full_name.split(' (')[0]}</h1>
          <p className="mt-2 max-w-xl text-muted">Balance Within. Harmony Around. Well-being for All.</p>
          <div className="mt-5 flex flex-wrap gap-2">
            {isInd && !loading && !dash?.has_data && <Link to="/assessment" className="btn-primary"><ClipboardList size={16} /> Start your 10-minute baseline</Link>}
            {isInd && dash?.has_data && <>
              <Link to="/dashboard" className="btn-primary"><LayoutDashboard size={16} /> Open my 360° dashboard</Link>
              {dash.overview.review_due && <Link to="/assessment" className="btn-saffron"><ClipboardList size={16} /> Quarterly check-in is due</Link>}
              <Link to="/habits" className="btn-ghost"><Repeat size={16} /> Today's micro-habits</Link>
            </>}
            {(user!.user_role === 'coach' || user!.user_role === 'counselor') && <>
              <Link to="/coach" className="btn-primary"><Stethoscope size={16} /> My clients</Link>
              <Link to="/interview" className="btn-ghost"><Mic size={16} /> Start an interview</Link>
            </>}
            {user!.user_role === 'admin' && <Link to="/admin" className="btn-primary"><Settings size={16} /> Administration</Link>}
          </div>
        </div>
      </section>

      {isInd && loading && <Spinner />}
      {isInd && dash?.has_data && (
        <section className="grid gap-4 md:grid-cols-3">
          <div className="card p-5">
            <div className="text-xs font-semibold uppercase tracking-wide text-muted">Snapshot · {dash.overview.last_assessment_date}</div>
            <div className="mt-2 flex items-baseline gap-2"><span className="font-display text-4xl font-semibold">{dash.overview.dimensions_assessed}</span><span className="text-muted">of 14 dimensions assessed</span></div>
            <p className="mt-2 text-sm">{dash.overview.improving} improving · {dash.overview.needs_attention} need attention</p>
            <p className="mt-1 text-xs text-muted">Next quarterly review {dash.overview.next_review_date}</p>
          </div>
          <div className="card p-5 md:col-span-2">
            <div className="text-xs font-semibold uppercase tracking-wide text-muted">Focus for this quarter</div>
            <ul className="mt-3 space-y-3">
              {dash.priorities.slice(0, 3).map((p: any) => (
                <li key={p.category_id} className="flex items-center gap-3">
                  <CategoryIcon id={p.category_id} size={16} />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2 text-sm font-semibold">{p.category_name} <LevelBadge level={p.level} small /></div>
                    <div className="truncate text-xs text-muted">{p.micro_habits[0]?.habit ?? 'See recommendations'}</div>
                  </div>
                  <span className="text-sm font-semibold">{fmt(p.current)} → {fmt(p.target)}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {isInd && habits && habits.length > 0 && (
        <section className="card p-5">
          <div className="flex items-center justify-between"><h2 className="text-lg font-semibold">Today's gentle habits</h2><Link to="/habits" className="text-sm font-semibold text-teal">All habits <ArrowRight size={14} className="inline" /></Link></div>
          <div className="mt-3 flex flex-wrap gap-2">
            {habits.filter((h) => h.frequency === 'daily' && h.status === 'active').map((h) => (
              <span key={h.habit_id} className={`chip border ${h.done_today ? 'border-leaf text-leaf' : 'border-line text-ink'}`}>{h.done_today ? '✓ ' : ''}{h.habit_name}</span>
            ))}
          </div>
        </section>
      )}

      <section>
        <h2 className="text-xl font-semibold">Fourteen dimensions of a complete life</h2>
        <p className="mt-1 text-sm text-muted">Each dimension is assessed and shown independently — a strength in one never hides a concern in another.</p>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-7">
          {cats?.map((c) => (
            <div key={c.category_id} className="card flex flex-col items-center gap-2 p-4 text-center">
              <CategoryIcon id={c.category_id} size={18} />
              <span className="text-xs font-semibold leading-tight">{c.category_name}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-3 sm:grid-cols-4">
        {ASPIRATIONS.map((a, i) => <div key={a} className="rounded-2xl p-4 text-sm font-semibold" style={{ background: ['rgb(var(--teal-soft))', 'rgb(var(--saffron-soft))', 'rgb(var(--teal-soft))', 'rgb(var(--saffron-soft))'][i] }}>{a}</div>)}
      </section>
      <Disclaimer />
    </div>
  )
}
