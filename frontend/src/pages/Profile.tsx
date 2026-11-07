import { useState } from 'react'
import { useAuth } from '../lib/auth'
import { api } from '../lib/api'
import { useApi } from '../lib/hooks'
import { PageHeader, Spinner } from '../components/ui'

export default function Profile() {
  const { user, refresh } = useAuth()
  const { data: prefs, setData: setPrefs } = useApi<any>('/me/preferences')
  const [f, setF] = useState({ full_name: user!.full_name, phone_number: user!.phone_number ?? '', occupation: user!.occupation ?? '', industry: user!.industry ?? '', age_group: user!.age_group ?? '', city: user!.city ?? '' })
  const [msg, setMsg] = useState<string | null>(null)
  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    await api('/me/profile', { method: 'PUT', body: Object.fromEntries(Object.entries(f).map(([k, v]) => [k, v || null])) })
    await refresh(); setMsg('Profile updated.')
  }
  const setPref = async (k: string, v: any) => setPrefs(await api('/me/preferences', { method: 'PUT', body: { [k]: v } }))
  const field = (k: keyof typeof f, label: string, type = 'text') => (
    <div><label className="label" htmlFor={k}>{label}</label><input id={k} type={type} className="input" value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></div>
  )
  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader title="My Profile" subtitle={`${user!.email} · ${user!.user_role} · member since ${user!.registration_date}`} />
      <form onSubmit={save} className="card grid gap-4 p-5 sm:grid-cols-2">
        {field('full_name', 'Full name')}{field('phone_number', 'Phone (optional)', 'tel')}{field('occupation', 'Occupation')}{field('industry', 'Industry')}
        <div><label className="label" htmlFor="age">Age group</label><select id="age" className="input" value={f.age_group} onChange={(e) => setF({ ...f, age_group: e.target.value })}><option value="">Prefer not to say</option>{['18-29', '30-39', '40-49', '50-59', '60+'].map((a) => <option key={a}>{a}</option>)}</select></div>
        {field('city', 'City')}
        <div className="flex items-center gap-3 sm:col-span-2"><button className="btn-primary">Save changes</button>{msg && <span className="text-sm text-leaf">{msg}</span>}</div>
      </form>
      <section className="card p-5">
        <h2 className="text-lg font-semibold">Preferences</h2>
        {!prefs ? <Spinner /> : (
          <div className="mt-3 space-y-3 text-sm">
            <label className="flex items-center justify-between gap-3"><span>Gentle habit & review reminders</span><input type="checkbox" checked={prefs.reminders_enabled} onChange={(e) => setPref('reminders_enabled', e.target.checked)} className="h-5 w-5" /></label>
            <label className="flex items-center justify-between gap-3"><span>Language</span><select className="input w-40" value={prefs.language} onChange={(e) => setPref('language', e.target.value)}><option value="en">English</option><option value="hi" disabled>हिन्दी (coming soon)</option></select></label>
          </div>
        )}
      </section>
    </div>
  )
}
