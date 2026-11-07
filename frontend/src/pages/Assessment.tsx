import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, CheckCircle2 } from 'lucide-react'
import clsx from 'clsx'
import { api } from '../lib/api'
import { useApi } from '../lib/hooks'
import { CategoryStep, toPayload, type AnswerState, type Category } from '../components/QuestionForm'
import { CategoryIcon, Disclaimer, ErrorNote, LevelBadge, PageHeader, SafetyBanner, Spinner } from '../components/ui'
import { fmt } from '../lib/levels'

const DRAFT = 'swasti.assessment.draft'

export default function Assessment() {
  const { data: cats, loading, error } = useApi<Category[]>('/categories')
  const [step, setStep] = useState(-1)
  const [answers, setAnswers] = useState<Record<string, AnswerState>>({})
  const [comments, setComments] = useState<Record<string, string>>({})
  const [result, setResult] = useState<any>(null)
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    try { const d = JSON.parse(localStorage.getItem(DRAFT) || 'null'); if (d) { setAnswers(d.answers || {}); setComments(d.comments || {}) } } catch { /* no draft */ }
  }, [])
  useEffect(() => {
    try { localStorage.setItem(DRAFT, JSON.stringify({ answers, comments })) } catch { /* ignore */ }
  }, [answers, comments])

  const total = useMemo(() => cats?.reduce((n, c) => n + c.parameters.length, 0) ?? 0, [cats])
  const done = Object.keys(answers).length
  if (loading) return <Spinner />
  if (error || !cats) return <ErrorNote msg={error} />

  const submit = async () => {
    setBusy(true); setErr(null)
    try {
      const r = await api('/assessments', { method: 'POST', body: toPayload(cats, answers, comments) })
      setResult(r)
      try { localStorage.removeItem(DRAFT) } catch { /* ignore */ }
      window.scrollTo(0, 0)
    } catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }

  if (result) {
    const names = Object.fromEntries(cats.map((c) => [c.category_id, c.category_name]))
    return (
      <div>
        <SafetyBanner safety={result.safety} />
        <PageHeader title="Thank you — assessment saved" subtitle={`Your 14 wellness agents are now analysing your responses. ${result.assessment_type === 'baseline' ? 'This is your baseline.' : 'Your history is preserved so you can compare quarters.'}`}
          actions={<Link className="btn-primary" to="/dashboard">View my 360° dashboard <ArrowRight size={16} /></Link>} />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {result.scores.map((s: any) => (
            <div key={s.category_id} className="card flex items-center gap-3 p-4">
              <CategoryIcon id={s.category_id} size={16} />
              <div className="flex-1"><div className="text-sm font-semibold">{names[s.category_id]}</div><LevelBadge level={s.level} small /></div>
              <div className="font-display text-2xl font-semibold">{fmt(s.score)}</div>
            </div>
          ))}
        </div>
        <div className="mt-6"><Disclaimer /></div>
      </div>
    )
  }

  if (step === -1) {
    return (
      <div className="mx-auto max-w-2xl">
        <PageHeader title="Wellness Assessment" subtitle="Four short questions for each of the 14 dimensions — about 10 minutes. There are no right or wrong answers." />
        <div className="card space-y-4 p-6 text-sm">
          <p>Answer on a simple 1–5 scale. You can choose <b>Prefer not to answer</b> for any question, and <b>Not applicable</b> where it doesn't fit your life — these are left out of your score, never counted as zero.</p>
          <p>Your progress is saved on this device as you go, so you can pause and return.</p>
          <p className="text-muted">If anything you're going through feels overwhelming right now, please call Tele-MANAS on <a className="font-semibold text-teal" href="tel:14416">14416</a> (free, 24×7) or emergency services on <a className="font-semibold text-teal" href="tel:112">112</a>.</p>
          <button className="btn-primary" onClick={() => setStep(0)}>{done ? `Continue (${done}/${total} answered)` : 'Begin'} <ArrowRight size={16} /></button>
        </div>
      </div>
    )
  }

  const cat = cats[step]
  const isLast = step === cats.length - 1
  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-5">
        <div className="mb-2 flex justify-between text-xs font-semibold text-muted"><span>Dimension {step + 1} of {cats.length}</span><span>{done}/{total} answered</span></div>
        <div className="flex gap-1" aria-hidden>
          {cats.map((c, i) => {
            const n = c.parameters.filter((p) => answers[p.parameter_id]).length
            return <button key={c.category_id} onClick={() => setStep(i)} title={c.category_name}
              className={clsx('h-2 flex-1 rounded-full', i === step ? 'bg-saffron' : n === c.parameters.length ? 'bg-teal' : n ? 'bg-teal/40' : 'bg-surface2')} />
          })}
        </div>
      </div>
      <CategoryStep cat={cat} answers={answers} setAnswer={(pid, a) => setAnswers((s) => { const n = { ...s }; if (a) n[pid] = a; else delete n[pid]; return n })}
        comment={comments[cat.category_id] ?? ''} setComment={(v) => setComments({ ...comments, [cat.category_id]: v })} />
      <ErrorNote msg={err} />
      <div className="sticky bottom-20 mt-6 flex justify-between gap-3 rounded-2xl bg-bg/90 py-3 backdrop-blur lg:bottom-0">
        <button className="btn-ghost" onClick={() => setStep(step - 1)}><ArrowLeft size={16} /> Back</button>
        {isLast
          ? <button className="btn-primary" disabled={busy || done === 0} onClick={submit}><CheckCircle2 size={16} /> {busy ? 'Saving…' : `Submit assessment (${done}/${total})`}</button>
          : <button className="btn-primary" onClick={() => { setStep(step + 1); window.scrollTo(0, 0) }}>Next <ArrowRight size={16} /></button>}
      </div>
    </div>
  )
}
