import { useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { AlertTriangle, ArrowRight, CalendarDays, Lightbulb, Link2, Loader2, RefreshCw } from 'lucide-react'
import { useApi } from '../lib/hooks'
import { useAuth } from '../lib/auth'
import { fmt, levelColor } from '../lib/levels'
import { CategoryIcon, Delta, Disclaimer, Empty, ErrorNote, LevelBadge, LevelLegend, PageHeader, ProgressBar, SafetyBanner, Spinner, Stat } from '../components/ui'
import { HabitBars, OverallTrend, Sparkline, WellnessRadar } from '../components/charts'

export default function Dashboard() {
  const [sp] = useSearchParams()
  const uid = sp.get('user_id')
  const { user } = useAuth()
  const q = uid ? `?user_id=${uid}` : ''
  const { data: d, loading, error, reload } = useApi<any>(`/dashboard${q}`, [uid])
  const pending = d?.overview?.agents_status && ['pending', 'running'].includes(d.overview.agents_status)
  useEffect(() => {
    if (!pending) return
    const t = setTimeout(reload, 2500)
    return () => clearTimeout(t)
  }, [pending, d, reload])

  if (loading && !d) return <Spinner label="Loading your 360° view…" />
  if (error) return <ErrorNote msg={error} />
  if (!d?.has_data) return (
    <Empty title="No assessment yet">
      {user?.user_role === 'individual' ? <Link to="/assessment" className="btn-primary mt-4">Take your baseline assessment</Link> : 'This person has not completed an assessment.'}
    </Empty>
  )
  const o = d.overview
  return (
    <div className="space-y-8">
      <SafetyBanner safety={d.safety} />
      <PageHeader title="360° Wellness Dashboard" subtitle={<>Fourteen dimensions, each shown on its own. Last assessed {o.last_assessment_date} · {o.assessments_count} assessment{o.assessments_count > 1 ? 's' : ''} on record.</>}
        actions={<>
          {pending && <span className="chip border border-line text-muted"><Loader2 size={13} className="animate-spin" /> Agents analysing…</span>}
          <button className="btn-ghost" onClick={reload} aria-label="Refresh"><RefreshCw size={15} /></button>
          {!uid && <Link to="/assessment" className={o.review_due ? 'btn-saffron' : 'btn-ghost'}>{o.review_due ? 'Quarterly check-in due' : 'Reassess'}</Link>}
        </>} />

      {/* A. Overview */}
      <section className="grid grid-cols-2 gap-3 lg:grid-cols-6" aria-label="Overview">
        <div className="card col-span-2 flex items-center gap-4 p-4">
          <div className="grid h-20 w-20 shrink-0 place-items-center rounded-full border-[6px]" style={{ borderColor: 'rgb(var(--teal))' }}>
            <span className="font-display text-2xl font-semibold">{o.overall_indicator !== null ? fmt(o.overall_indicator) : '—'}</span>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-muted">Overall wellness indicator</div>
            <p className="mt-1 text-xs text-muted">{o.overall_indicator !== null ? 'A secondary summary. Always read it alongside the 14 individual scores.' : 'Not enough dimensions answered for a reliable overall figure.'}</p>
          </div>
        </div>
        <Stat label="Assessed" value={`${o.dimensions_assessed}/${o.dimensions_total}`} hint={`coverage ${Math.round((o.coverage ?? 0) * 100)}%`} />
        <Stat label="Need attention" value={o.needs_attention} hint="below 40" />
        <Stat label="Improving" value={o.improving} hint={o.declining ? `${o.declining} lower` : 'vs last quarter'} />
        <Stat label="Next review" value={<span className="text-lg">{o.next_review_date}</span>} hint={o.review_due ? 'due now' : 'every 3 months'} />
      </section>

      {d.attention_flags.length > 0 && (
        <div className="card flex gap-3 p-4" style={{ borderColor: 'var(--lv-attention)' }}>
          <AlertTriangle className="shrink-0" style={{ color: 'var(--lv-attention)' }} aria-hidden />
          <p className="text-sm"><b>Gentle attention suggested:</b> {d.attention_flags.map((f: any) => `${f.category_name} (${fmt(f.score)})`).join(', ')}. These are shown on their own so a strong overall figure never hides them.</p>
        </div>
      )}

      {/* B. Fourteen cards */}
      <section aria-label="Fourteen wellness dimensions">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2"><h2 className="text-xl font-semibold">Your fourteen dimensions</h2><LevelLegend /></div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {d.cards.map((c: any) => (
            <article key={c.category_id} className="card flex flex-col gap-3 p-4">
              <div className="flex items-start gap-3">
                <CategoryIcon id={c.category_id} size={18} />
                <div className="min-w-0 flex-1">
                  <h3 className="font-sans text-sm font-semibold">{c.category_name}</h3>
                  <div className="mt-1"><LevelBadge level={c.level} small /></div>
                </div>
                <div className="text-right">
                  <div className="font-display text-3xl font-semibold leading-none" style={{ color: c.current !== null ? levelColor(c.level) : undefined }}>{fmt(c.current)}</div>
                  <div className="text-[11px] text-muted">target {fmt(c.achievable_target ?? c.target)}</div>
                </div>
              </div>
              <ProgressBar value={c.current} target={c.achievable_target ?? c.target} color={levelColor(c.level)} />
              <div className="flex items-center justify-between">
                <Delta value={c.change} />
                <Link to={`/dashboard/${c.category_id}${q}`} className="inline-flex min-h-[36px] items-center gap-1 text-xs font-semibold text-teal">View details <ArrowRight size={13} /></Link>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* C. Radar */}
      <section className="card p-4 sm:p-6" aria-label="Wellness radar">
        <h2 className="text-xl font-semibold">Wellness radar</h2>
        <p className="mb-3 text-sm text-muted">Compare your initial assessment, previous quarter, current quarter and target across all 14 axes.</p>
        <WellnessRadar data={d.radar} />
      </section>

      {/* D. Progress */}
      <section className="grid gap-4 lg:grid-cols-2" aria-label="Progress">
        <div className="card p-4 sm:p-6">
          <h2 className="text-lg font-semibold">Overall trend by quarter</h2>
          {d.trend.length > 1 ? <OverallTrend data={d.trend} /> : <p className="py-10 text-center text-sm text-muted">Trends appear after your next quarterly check-in.</p>}
        </div>
        <div className="card p-4 sm:p-6">
          <h2 className="text-lg font-semibold">Micro-habit completions</h2>
          {d.habit_trend.length ? <HabitBars data={d.habit_trend} /> : <p className="py-10 text-center text-sm text-muted">Track a micro-habit to see your consistency here.</p>}
        </div>
      </section>
      {d.trend.length > 1 && (
        <section aria-label="Category trends">
          <h2 className="mb-1 text-lg font-semibold">Dimension trends</h2>
          <p className="mb-3 text-sm text-muted">One small chart per dimension; dashed line is the target.</p>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
            {d.cards.map((c: any) => (
              <div key={c.category_id} className="card p-3">
                <div className="flex items-center justify-between text-xs font-semibold"><span className="truncate">{c.category_name.replace(' Wellness', '')}</span>{c.direction && <span className={c.direction === 'improved' ? 'text-leaf' : c.direction === 'declined' ? 'text-saffron' : 'text-muted'}>{c.direction === 'improved' ? '▲' : c.direction === 'declined' ? '▼' : '•'}</span>}</div>
                <Sparkline data={d.trend} dataKey={c.category_id} target={c.target} />
              </div>
            ))}
          </div>
        </section>
      )}

      {/* E & F. Recommendations + insights */}
      <section className="grid gap-4 lg:grid-cols-5">
        <div className="card p-4 sm:p-6 lg:col-span-3">
          <div className="flex items-center justify-between"><h2 className="text-lg font-semibold">Top improvement priorities</h2>{!uid && <Link to="/recommendations" className="text-sm font-semibold text-teal">All recommendations</Link>}</div>
          <ol className="mt-4 space-y-4">
            {d.priorities.map((p: any, i: number) => (
              <li key={p.category_id} className="flex gap-3">
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-saffron-soft text-xs font-bold text-saffron">{i + 1}</span>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2 text-sm font-semibold">{p.category_name}<span className="text-xs font-normal text-muted">{fmt(p.current)} → {fmt(p.target)}</span></div>
                  {p.actions.slice(0, 1).map((a: any) => <p key={a.recommendation_id} className="text-sm text-muted">{a.action}</p>)}
                </div>
              </li>
            ))}
            {d.priorities.length === 0 && <p className="text-sm text-muted">Every assessed dimension is at or above its target — focus on sustaining what works.</p>}
          </ol>
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <div><h3 className="font-sans text-xs font-semibold uppercase tracking-wide text-muted">Daily ideas</h3><ul className="mt-2 space-y-1 text-sm">{d.daily_habits.map((h: any) => <li key={h.recommendation_id}>• {h.habit}</li>)}</ul></div>
            <div><h3 className="font-sans text-xs font-semibold uppercase tracking-wide text-muted">Weekly ideas</h3><ul className="mt-2 space-y-1 text-sm">{d.weekly_habits.map((h: any) => <li key={h.recommendation_id}>• {h.habit}</li>)}</ul></div>
          </div>
          <p className="mt-4 flex items-center gap-2 text-xs text-muted"><CalendarDays size={14} /> Next quarterly review: {o.next_review_date}</p>
        </div>
        <div className="card p-4 sm:p-6 lg:col-span-2">
          <h2 className="flex items-center gap-2 text-lg font-semibold"><Link2 size={18} className="text-teal" /> Cross-wellness insights</h2>
          <p className="mt-1 text-xs text-muted">Patterns from your own answers. They describe things that move together — not causes.</p>
          <ul className="mt-4 space-y-3">
            {d.insights.map((i: any, k: number) => (
              <li key={k} className="rounded-xl bg-surface2 p-3 text-sm">
                <div className="mb-1 flex gap-1">{i.categories.map((c: string) => <CategoryIcon key={c} id={c} size={11} />)}</div>
                {i.message}
              </li>
            ))}
            {d.insights.length === 0 && <li className="flex gap-2 text-sm text-muted"><Lightbulb size={16} /> No linked patterns stand out in this assessment.</li>}
          </ul>
        </div>
      </section>
      <Disclaimer>{d.disclaimer} Level bands are provisional application indicators, not clinically validated thresholds.</Disclaimer>
    </div>
  )
}
