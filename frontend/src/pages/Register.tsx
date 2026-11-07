import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AuthShell } from './Login'
import { useAuth } from '../lib/auth'

export default function Register() {
  const { register } = useAuth()
  const nav = useNavigate()
  const [f, setF] = useState({ full_name: '', email: '', password: '', occupation: '', industry: '', age_group: '', city: '', consent_data_processing: false, consent_ai_analysis: false })
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const set = (k: string) => (e: any) => setF({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null)
    try { await register({ ...f, occupation: f.occupation || null, industry: f.industry || null, age_group: f.age_group || null, city: f.city || null }); nav('/assessment') }
    catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  return (
    <AuthShell>
      <form onSubmit={submit} className="w-full max-w-md space-y-4">
        <h2 className="text-3xl font-semibold">Create your account</h2>
        <p className="text-sm text-muted">We only ask what's needed. Occupation and city are optional and help personalise suggestions.</p>
        <div><label className="label" htmlFor="n">Full name</label><input id="n" className="input" value={f.full_name} onChange={set('full_name')} required minLength={2} /></div>
        <div><label className="label" htmlFor="e">Email</label><input id="e" className="input" type="email" value={f.email} onChange={set('email')} required /></div>
        <div><label className="label" htmlFor="p">Password (min 8 characters)</label><input id="p" className="input" type="password" value={f.password} onChange={set('password')} required minLength={8} autoComplete="new-password" /></div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label" htmlFor="o">Occupation</label><input id="o" className="input" value={f.occupation} onChange={set('occupation')} /></div>
          <div><label className="label" htmlFor="i">Industry</label><input id="i" className="input" value={f.industry} onChange={set('industry')} /></div>
          <div><label className="label" htmlFor="a">Age group</label>
            <select id="a" className="input" value={f.age_group} onChange={set('age_group')}><option value="">Prefer not to say</option>{['18-29', '30-39', '40-49', '50-59', '60+'].map((a) => <option key={a}>{a}</option>)}</select></div>
          <div><label className="label" htmlFor="c">City</label><input id="c" className="input" value={f.city} onChange={set('city')} /></div>
        </div>
        <fieldset className="space-y-3 rounded-2xl bg-surface2 p-4 text-sm">
          <legend className="sr-only">Consent</legend>
          <label className="flex gap-3"><input type="checkbox" className="mt-1 h-4 w-4 accent-[rgb(var(--teal))]" checked={f.consent_data_processing} onChange={set('consent_data_processing')} required />
            <span><b>Required:</b> I consent to SAMPURNA processing my self-reported wellness information to calculate my scores and recommendations, as described in the privacy notice (DPDP Act, 2023). I can withdraw consent and delete my data at any time. My employer cannot see my individual results.</span></label>
          <label className="flex gap-3"><input type="checkbox" className="mt-1 h-4 w-4" checked={f.consent_ai_analysis} onChange={set('consent_ai_analysis')} />
            <span><b>Optional:</b> Allow an AI language model to rephrase my agent summaries. Only scores and dimension names are sent — never my name, contact details or comments.</span></label>
        </fieldset>
        {err && <p className="text-sm" style={{ color: 'var(--lv-attention)' }} role="alert">{err}</p>}
        <button className="btn-primary w-full" disabled={busy}>{busy ? 'Creating…' : 'Create account & start'}</button>
        <p className="text-center text-sm text-muted">Already registered? <Link to="/login" className="font-semibold text-teal">Sign in</Link></p>
      </form>
    </AuthShell>
  )
}
