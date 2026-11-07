import { useState } from 'react'
import { BookOpen, CheckCircle2, ExternalLink, Plus, ShieldAlert, Sparkles } from 'lucide-react'
import { api } from '../lib/api'
import { fmt } from '../lib/levels'
import { Delta, LevelBadge, ScoreRing } from './ui'

export function EvidenceLink({ e }: { e: any }) {
  return (
    <a href={e.url} target="_blank" rel="noreferrer" className="flex items-start gap-2 rounded-xl border border-line p-3 text-xs hover:bg-surface2">
      <BookOpen size={14} className="mt-0.5 shrink-0 text-teal" aria-hidden />
      <span className="min-w-0 flex-1"><span className="font-semibold text-ink">{e.title}</span><br /><span className="text-muted">{e.organization}</span>
        <span className="ml-2 chip border border-line px-1.5 text-[10px] text-muted">{e.verification_status === 'verified' ? `verified ${e.last_verified_date}` : 'link pending expert verification'}</span></span>
      <ExternalLink size={12} className="shrink-0 text-muted" aria-hidden />
    </a>
  )
}

export function AgentOutput({ out, names, canPlan }: { out: any; names?: Record<string, string>; canPlan?: boolean }) {
  const [added, setAdded] = useState<Record<string, boolean>>({})
  const addPlan = async (rid: string) => { await api('/plans', { method: 'POST', body: { recommendation_id: rid } }); setAdded({ ...added, [rid]: true }) }
  const evidence = Object.fromEntries((out.evidence_references ?? []).map((e: any) => [e.reference_id, e]))
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-6">
        <ScoreRing value={out.current_score} level={out.current_level} label="current" />
        <div className="space-y-2">
          <LevelBadge level={out.current_level} />
          <div className="text-sm">Achievable next-quarter target: <b>{fmt(out.target_score)}</b> ({out.target_level}) · benchmark {fmt(out.benchmark_target)}</div>
          <Delta value={out.change_since_previous} />
          <div className="text-xs text-muted">Confidence <b>{out.confidence_level}</b> · coverage {Math.round(out.coverage * 100)}% · review in {out.review_interval_days} days · agent {out.agent_id} v{out.agent_version}</div>
        </div>
      </div>
      <p className="rounded-2xl bg-surface2 p-4 text-sm">{out.progress_report}</p>
      {out.ai_narrative && <p className="flex gap-2 rounded-2xl border border-dashed border-line p-4 text-sm"><Sparkles size={16} className="shrink-0 text-saffron" /><span>{out.ai_narrative.text}<br /><span className="text-xs text-muted">{out.ai_narrative.label}</span></span></p>}
      {out.specialised_notes?.length > 0 && <ul className="space-y-1 text-sm">{out.specialised_notes.map((n: string) => <li key={n} className="flex gap-2"><ShieldAlert size={15} className="mt-0.5 shrink-0 text-saffron" />{n}</li>)}</ul>}
      <div className="grid gap-4 md:grid-cols-2">
        <div><h4 className="label">Strengths</h4>
          {out.strengths.length ? <ul className="space-y-1 text-sm">{out.strengths.map((s: any) => <li key={s.parameter_id} className="flex justify-between"><span className="flex items-center gap-1.5"><CheckCircle2 size={14} className="text-leaf" />{s.name}</span><span className="tabular-nums text-muted">{fmt(s.score)}</span></li>)}</ul> : <p className="text-sm text-muted">Building — keep going.</p>}
        </div>
        <div><h4 className="label">Room to grow</h4>
          {out.improvement_areas.length ? <ul className="space-y-1 text-sm">{out.improvement_areas.map((s: any) => <li key={s.parameter_id} className="flex justify-between"><span>{s.name}</span><span className="tabular-nums text-muted">{fmt(s.score)}</span></li>)}</ul> : <p className="text-sm text-muted">No item scored 50 or below.</p>}
        </div>
      </div>
      <div>
        <h4 className="label">Recommended actions (evidence-linked)</h4>
        <div className="space-y-3">
          {out.recommended_actions.map((a: any) => (
            <div key={a.recommendation_id} className="rounded-2xl border border-line p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div><div className="font-semibold">{a.title}</div><p className="text-sm">{a.action}</p><p className="mt-1 text-xs text-muted">Why: {a.rationale}{a.addresses?.length ? ` · Addresses: ${a.addresses.join(', ')}` : ''}</p></div>
                {canPlan && <button className="btn-ghost text-xs" disabled={added[a.recommendation_id]} onClick={() => addPlan(a.recommendation_id)}>{added[a.recommendation_id] ? <><CheckCircle2 size={14} /> In my plan</> : <><Plus size={14} /> Add to plan & habits</>}</button>}
              </div>
              {evidence[a.evidence_reference] && <div className="mt-3"><EvidenceLink e={evidence[a.evidence_reference]} /></div>}
            </div>
          ))}
        </div>
      </div>
      {out.suggested_micro_habits.length > 0 && <div><h4 className="label">Suggested micro-habits</h4><div className="flex flex-wrap gap-2">{out.suggested_micro_habits.map((h: any) => <span key={h.recommendation_id} className="chip border border-line">{h.habit} · {h.frequency}</span>)}</div></div>}
      <p className="text-xs text-muted">{out.disclaimer}{names ? '' : ''}</p>
    </div>
  )
}
