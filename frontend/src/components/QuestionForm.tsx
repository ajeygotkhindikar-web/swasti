import clsx from 'clsx'
import { CategoryIcon } from './ui'

export interface Param { parameter_id: string; name: string; question: string; response_type: string; options: { value: number; label: string }[]; allow_not_applicable: boolean }
export interface Category { category_id: string; category_name: string; description: string; icon: string; parameters: Param[] }
export interface AnswerState { value: number | null; status: 'answered' | 'not_applicable' | 'prefer_not_to_answer' }

export function QuestionBlock({ p, a, onChange, index }: { p: Param; a?: AnswerState; onChange: (a: AnswerState | undefined) => void; index: number }) {
  return (
    <fieldset className="card p-4 sm:p-5">
      <legend className="sr-only">{p.question}</legend>
      <p className="font-medium"><span className="mr-2 text-muted">{index}.</span>{p.question}</p>
      <div className={clsx('mt-3 grid gap-2', p.options.length === 2 ? 'grid-cols-2' : 'grid-cols-1 sm:grid-cols-5')}>
        {p.options.map((o) => {
          const sel = a?.status === 'answered' && a.value === o.value
          return (
            <button type="button" key={o.value} aria-pressed={sel} onClick={() => onChange({ value: o.value, status: 'answered' })}
              className={clsx('flex min-h-[48px] items-center gap-2 rounded-xl border px-3 py-2 text-left text-sm transition sm:flex-col sm:justify-center sm:text-center',
                sel ? 'border-teal bg-teal text-onteal' : 'border-line bg-surface hover:border-teal')}>
              {p.options.length > 2 && <span className={clsx('grid h-6 w-6 shrink-0 place-items-center rounded-full text-xs font-bold', sel ? 'bg-white/20' : 'bg-surface2')}>{o.value}</span>}
              <span>{o.label}</span>
            </button>
          )
        })}
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {p.allow_not_applicable && (
          <button type="button" aria-pressed={a?.status === 'not_applicable'} onClick={() => onChange({ value: null, status: 'not_applicable' })}
            className={clsx('chip border min-h-[32px]', a?.status === 'not_applicable' ? 'border-teal bg-teal-soft text-teal' : 'border-line text-muted')}>Not applicable</button>
        )}
        <button type="button" aria-pressed={a?.status === 'prefer_not_to_answer'} onClick={() => onChange({ value: null, status: 'prefer_not_to_answer' })}
          className={clsx('chip border min-h-[32px]', a?.status === 'prefer_not_to_answer' ? 'border-teal bg-teal-soft text-teal' : 'border-line text-muted')}>Prefer not to answer</button>
        {a && <button type="button" className="chip min-h-[32px] text-muted underline" onClick={() => onChange(undefined)}>Clear</button>}
      </div>
    </fieldset>
  )
}

export function CategoryStep({ cat, answers, setAnswer, comment, setComment, commentLabel = 'Anything you would like to add? (optional)' }: {
  cat: Category; answers: Record<string, AnswerState>; setAnswer: (pid: string, a: AnswerState | undefined) => void
  comment: string; setComment: (s: string) => void; commentLabel?: string
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <CategoryIcon id={cat.category_id} size={22} />
        <div><h2 className="text-xl font-semibold">{cat.category_name}</h2><p className="text-sm text-muted">{cat.description}</p></div>
      </div>
      {cat.parameters.map((p, i) => <QuestionBlock key={p.parameter_id} p={p} index={i + 1} a={answers[p.parameter_id]} onChange={(a) => setAnswer(p.parameter_id, a)} />)}
      <div>
        <label className="label" htmlFor={`c-${cat.category_id}`}>{commentLabel}</label>
        <textarea id={`c-${cat.category_id}`} className="input min-h-[80px] py-2" maxLength={1000} value={comment} onChange={(e) => setComment(e.target.value)} />
      </div>
    </div>
  )
}

export function toPayload(cats: Category[], answers: Record<string, AnswerState>, comments: Record<string, string>) {
  const list = cats.flatMap((c) => c.parameters).filter((p) => answers[p.parameter_id])
    .map((p) => ({ parameter_id: p.parameter_id, value: answers[p.parameter_id].value, status: answers[p.parameter_id].status }))
  const cc = Object.fromEntries(Object.entries(comments).filter(([, v]) => v.trim()))
  return { answers: list, category_comments: cc }
}
