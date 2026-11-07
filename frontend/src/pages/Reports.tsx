import { useState } from 'react'
import { Download, FileText } from 'lucide-react'
import { downloadPdf } from '../lib/api'
import { useApi } from '../lib/hooks'
import { useAuth } from '../lib/auth'
import { ErrorNote, PageHeader } from '../components/ui'

export default function Reports() {
  const { user } = useAuth()
  const isPro = user?.user_role !== 'individual'
  const { data: clients } = useApi<any[]>(isPro ? '/coach/clients' : null)
  const [who, setWho] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const get = async (kind: string) => {
    setBusy(true); setErr(null)
    try { await downloadPdf(`/reports/pdf?kind=${kind}${who ? `&user_id=${who}` : ''}`, `swasti-${kind}-report.pdf`) } catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  return (
    <div className="max-w-3xl">
      <PageHeader title="Wellness Reports" subtitle="Downloadable PDF reports in the SWASTI format. Reports include only information the viewer is authorised to see." />
      <ErrorNote msg={err} />
      {isPro && (
        <div className="card mb-4 p-4">
          <label className="label" htmlFor="who">Client (consented only)</label>
          <select id="who" className="input" value={who} onChange={(e) => setWho(e.target.value)}>
            <option value="">Select a client…</option>
            {clients?.filter((c) => c.scopes.includes('reports')).map((c) => <option key={c.user_id} value={c.user_id}>{c.full_name}</option>)}
          </select>
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-2">
        {(!isPro ? [['individual', 'Personal wellness report', 'Overview, 14 scores, radar, quarter comparison, strengths, recommendations and next-quarter plan.']] :
          [['individual', 'Client summary report', 'The individual report for your client.'], ['coach', 'Coach report', 'Adds your interview observations, follow-up history, progress trend and agreed actions.']]).map(([k, t, d]) => (
          <div key={k} className="card flex flex-col gap-3 p-5">
            <FileText className="text-teal" />
            <h2 className="text-lg font-semibold">{t}</h2>
            <p className="flex-1 text-sm text-muted">{d}</p>
            <button className="btn-primary" disabled={busy || (isPro && !who)} onClick={() => get(k)}><Download size={16} /> Download PDF</button>
          </div>
        ))}
      </div>
    </div>
  )
}
