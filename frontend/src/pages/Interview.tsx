import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import clsx from 'clsx'
import { Mic, MicOff, Save, Sparkles } from 'lucide-react'
import { api } from '../lib/api'
import { useApi } from '../lib/hooks'
import { CategoryStep, toPayload, type AnswerState, type Category } from '../components/QuestionForm'
import { CategoryIcon, Empty, ErrorNote, PageHeader, SafetyBanner, Spinner } from '../components/ui'

export default function Interview() {
  const [sp] = useSearchParams()
  const { data: clients } = useApi<any[]>('/coach/clients')
  const { data: cats } = useApi<Category[]>('/categories')
  const [client, setClient] = useState(sp.get('user_id') ?? '')
  const [active, setActive] = useState(0)
  const [answers, setAnswers] = useState<Record<string, AnswerState>>({})
  const [obs, setObs] = useState<Record<string, string>>({})
  const [summary, setSummary] = useState('')
  const [followPlan, setFollowPlan] = useState('')
  const [followDate, setFollowDate] = useState('')
  const [transcript, setTranscript] = useState('')
  const [useVoice, setUseVoice] = useState(false)
  const [listening, setListening] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [draft, setDraft] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const rec = useRef<any>(null)
  const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

  useEffect(() => () => rec.current?.stop(), [])
  if (!clients || !cats) return <Spinner />
  const eligible = clients.filter((c) => c.scopes.includes('interviews'))
  if (!eligible.length) return <Empty title="No consented clients">Individuals must grant you “interviews” access from their Privacy & Consent page before you can interview them.</Empty>

  const toggleVoice = () => {
    if (!SR) return
    if (listening) { rec.current?.stop(); setListening(false); return }
    const r = new SR(); r.lang = 'en-IN'; r.continuous = true; r.interimResults = false
    r.onresult = (e: any) => { const t = Array.from(e.results).slice(e.resultIndex).map((x: any) => x[0].transcript).join(' '); setTranscript((s) => (s + ' ' + t).trim()) }
    r.onend = () => setListening(false)
    r.start(); rec.current = r; setListening(true)
  }

  const save = async () => {
    setBusy(true); setErr(null)
    try {
      const p = toPayload(cats, answers, {})
      const r = await api('/interviews', { method: 'POST', body: {
        user_id: client, answers: p.answers, observations: Object.fromEntries(Object.entries(obs).filter(([, v]) => v.trim())),
        interview_summary: summary || null, transcript: useVoice && transcript ? transcript : null,
        follow_up_plan: followPlan || null, follow_up_date: followDate || null,
      } })
      setResult(r); window.scrollTo(0, 0)
    } catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  const getDraft = async () => { const d = await api(`/interviews/${result.interview.interview_id}/ai-summary`, { method: 'POST' }); setDraft(d.draft) }
  const saveDraft = async () => { await api(`/interviews/${result.interview.interview_id}`, { method: 'PATCH', body: { interview_summary: draft } }); setResult({ ...result, interview: { ...result.interview, interview_summary: draft } }); setDraft(null) }

  if (result) return (
    <div className="max-w-3xl space-y-4">
      <SafetyBanner safety={result.safety} />
      <PageHeader title="Interview saved" subtitle={`Responses were stored as an interview-sourced assessment for ${result.interview.user_name}. All 14 agents are analysing it now.`} />
      <div className="card space-y-3 p-5">
        <h3 className="font-semibold">Interview summary</h3>
        <p className="text-sm">{result.interview.interview_summary || <span className="text-muted">No summary yet.</span>}</p>
        <button className="btn-ghost" onClick={getDraft}><Sparkles size={15} /> Draft a summary from recorded data</button>
        {draft !== null && (
          <div className="space-y-2">
            <p className="text-xs text-muted">AI-assisted draft. It is not saved until you review and confirm. It never changes the individual's answers or scores.</p>
            <textarea className="input min-h-[120px] py-2" value={draft} onChange={(e) => setDraft(e.target.value)} />
            <button className="btn-primary" onClick={saveDraft}><Save size={15} /> Confirm & save summary</button>
          </div>
        )}
      </div>
      <a className="btn-primary" href={`/dashboard?user_id=${client}`}>Open client dashboard</a>
    </div>
  )

  const cat = cats[active]
  const answeredIn = (c: Category) => c.parameters.filter((p) => answers[p.parameter_id]).length
  return (
    <div>
      <PageHeader title="Interview Assessment" subtitle="Ask the standardised questions conversationally and record answers on the same 1–5 scale. Answer as many dimensions as you cover — unanswered ones are excluded, not scored as zero." />
      <div className="card mb-5 grid gap-3 p-4 sm:grid-cols-3">
        <div className="sm:col-span-2">
          <label className="label" htmlFor="cl">Individual</label>
          <select id="cl" className="input" value={client} onChange={(e) => setClient(e.target.value)}>
            <option value="">Select a consented individual…</option>
            {eligible.map((c) => <option key={c.user_id} value={c.user_id}>{c.full_name}{c.occupation ? ` — ${c.occupation}` : ''}</option>)}
          </select>
        </div>
        <div className="text-xs text-muted sm:pt-6">Interview date and your interviewer ID are recorded automatically.</div>
      </div>
      {client && (
        <div className="grid gap-5 lg:grid-cols-[15rem_1fr]">
          <nav className="flex gap-2 overflow-x-auto pb-2 lg:flex-col lg:overflow-visible" aria-label="Dimensions">
            {cats.map((c, i) => (
              <button key={c.category_id} onClick={() => setActive(i)} className={clsx('flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-left text-sm', i === active ? 'bg-teal-soft font-semibold text-teal' : 'hover:bg-surface2')}>
                <CategoryIcon id={c.category_id} size={12} framed={false} /> <span className="flex-1">{c.category_name.replace(' Wellness', '')}</span>
                <span className="text-xs text-muted">{answeredIn(c)}/{c.parameters.length}</span>
              </button>
            ))}
          </nav>
          <div className="space-y-5">
            <CategoryStep cat={cat} answers={answers} setAnswer={(pid, a) => setAnswers((s) => { const n = { ...s }; if (a) n[pid] = a; else delete n[pid]; return n })}
              comment={obs[cat.category_id] ?? ''} setComment={(v) => setObs({ ...obs, [cat.category_id]: v })} commentLabel="Interviewer observation for this dimension (optional)" />
            <div className="card space-y-3 p-4">
              <h3 className="font-semibold">Wrap-up</h3>
              <div><label className="label" htmlFor="sum">Interview summary</label><textarea id="sum" className="input min-h-[80px] py-2" value={summary} onChange={(e) => setSummary(e.target.value)} /></div>
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="sm:col-span-2"><label className="label" htmlFor="fp">Agreed follow-up actions</label><input id="fp" className="input" value={followPlan} onChange={(e) => setFollowPlan(e.target.value)} /></div>
                <div><label className="label" htmlFor="fd">Follow-up date</label><input id="fd" type="date" className="input" value={followDate} onChange={(e) => setFollowDate(e.target.value)} /></div>
              </div>
              <label className="flex gap-2 text-sm"><input type="checkbox" checked={useVoice} onChange={(e) => setUseVoice(e.target.checked)} className="mt-1" />
                <span>Record a voice-to-text transcript. Only works if the individual has granted <b>interview transcription</b> consent in their app; transcripts are stored encrypted, separately from scores.</span></label>
              {useVoice && (
                <div className="space-y-2">
                  {SR ? <button type="button" className={listening ? 'btn-saffron' : 'btn-ghost'} onClick={toggleVoice}>{listening ? <><MicOff size={15} /> Stop dictation</> : <><Mic size={15} /> Start dictation</>}</button>
                    : <p className="text-xs text-muted">Speech recognition isn't available in this browser — type or paste the transcript instead.</p>}
                  <textarea className="input min-h-[100px] py-2" value={transcript} onChange={(e) => setTranscript(e.target.value)} placeholder="Transcript" />
                </div>
              )}
              <ErrorNote msg={err} />
              <button className="btn-primary" disabled={busy || !Object.keys(answers).length} onClick={save}><Save size={15} /> {busy ? 'Saving…' : `Save interview (${Object.keys(answers).length} answers)`}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
