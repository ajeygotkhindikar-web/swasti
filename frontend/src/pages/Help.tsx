import { Phone } from 'lucide-react'
import { useApi } from '../lib/hooks'
import { CategoryIcon, LevelLegend, PageHeader } from '../components/ui'

const FAQ: [string, string][] = [
  ['Is my score a diagnosis?', 'No. Scores are self-assessment indicators to support reflection. They are not medical, psychological or financial assessments.'],
  ['How is a score calculated?', 'Each answer (1–5) becomes 0–100, reversed where a higher frequency is less healthy (e.g. stress). A dimension score is the weighted average of the questions you answered. "Not applicable" and "Prefer not to answer" are left out, never counted as zero. A dimension needs at least half its questions answered to be scored.'],
  ['Why is there no single headline score?', 'Someone can be financially secure but socially isolated, or physically fit but mentally exhausted. All 14 dimensions are always shown on their own; the overall indicator is secondary and is hidden when there is not enough data.'],
  ['What do the AI agents do?', 'Each of the 14 agents analyses one dimension, finds strengths and growth areas, sets an achievable target and selects actions from a curated knowledge base, each linked to a referenced source. They never diagnose, prescribe medicine or recommend financial products.'],
  ['Can my employer see my results?', 'No. Only people you explicitly approve can see your individual information. Organisational reports use anonymised averages for groups of at least five people.'],
  ['How often should I reassess?', 'Every three months. The same short questions are reused so changes are genuine, and all earlier results are kept.'],
  ['What if I miss my habits?', "That's fine. Micro-habits are invitations, not obligations — skip days freely and adjust or pause habits whenever you like."],
]

export default function Help() {
  const { data: cats } = useApi<any[]>('/categories')
  return (
    <div className="max-w-4xl space-y-6">
      <PageHeader title="Help & Resources" />
      <section className="card border-2 p-5" style={{ borderColor: 'var(--lv-attention)' }}>
        <h2 className="text-lg font-semibold">If you need support right now</h2>
        <p className="mt-1 text-sm text-muted">SAMPURNA is not an emergency service and its agents cannot respond to emergencies. Please reach out to a person:</p>
        <ul className="mt-3 space-y-2 text-sm">
          <li className="flex items-center gap-2"><Phone size={15} /> Emergency services (India): <a className="font-bold text-teal" href="tel:112">112</a></li>
          <li className="flex items-center gap-2"><Phone size={15} /> Tele-MANAS — free 24×7 mental health support (MoHFW): <a className="font-bold text-teal" href="tel:14416">14416</a> or <a className="font-bold text-teal" href="tel:18008914416">1-800-891-4416</a></li>
          <li className="flex items-center gap-2"><Phone size={15} /> Or contact a trusted person, or your nearest hospital emergency department.</li>
        </ul>
      </section>
      <section className="card p-5">
        <h2 className="text-lg font-semibold">Frequently asked questions</h2>
        <div className="mt-3 divide-y divide-line">{FAQ.map(([q, a]) => <details key={q} className="py-3"><summary className="cursor-pointer text-sm font-semibold">{q}</summary><p className="mt-2 text-sm text-muted">{a}</p></details>)}</div>
      </section>
      <section className="card p-5">
        <h2 className="text-lg font-semibold">Wellness levels</h2>
        <p className="mb-3 mt-1 text-sm text-muted">Provisional application indicators (configurable, not clinically validated): 0–39 Needs Attention · 40–59 Developing · 60–74 Balanced · 75–89 Good · 90–100 Thriving. Each level has its own colour, shape and label.</p>
        <LevelLegend />
      </section>
      <section className="card p-5">
        <h2 className="text-lg font-semibold">The 14 dimensions</h2>
        <ul className="mt-3 grid gap-3 sm:grid-cols-2">{cats?.map((c) => <li key={c.category_id} className="flex gap-3"><CategoryIcon id={c.category_id} size={14} /><div><div className="text-sm font-semibold">{c.category_name}</div><div className="text-xs text-muted">{c.description}</div></div></li>)}</ul>
      </section>
    </div>
  )
}
