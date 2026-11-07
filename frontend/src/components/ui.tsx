import type { ReactNode } from 'react'
import {
  AlertTriangle, Bike, Brain, Globe, HandHeart, HeartPulse, House, Landmark, Leaf, Music, Palette, Phone,
  ShieldCheck, Sparkles, TrendingDown, TrendingUp, Minus, Users, Wallet, Circle, Square, Triangle, Diamond, Star, Info,
} from 'lucide-react'
import clsx from 'clsx'
import { LEVELS, fmt, levelColor } from '../lib/levels'

const ICONS: Record<string, typeof Brain> = {
  brain: Brain, 'heart-pulse': HeartPulse, wallet: Wallet, 'shield-check': ShieldCheck, users: Users, sparkles: Sparkles,
  home: House, music: Music, leaf: Leaf, landmark: Landmark, 'hand-heart': HandHeart, bike: Bike, palette: Palette, globe: Globe,
}
const CAT_ICON: Record<string, string> = {
  MEN: 'brain', PHY: 'heart-pulse', FIN: 'wallet', PSY: 'shield-check', SOC: 'users', SPI: 'sparkles', FAM: 'home',
  MUS: 'music', ENV: 'leaf', CIV: 'landmark', EMP: 'hand-heart', SPO: 'bike', CUL: 'palette', UNI: 'globe',
}
// Each dimension gets its own tint so the 14 cards are recognisable at a glance.
const CAT_TINT: Record<string, string> = {
  MEN: '#2a78d6', PHY: '#d14b4b', FIN: '#b7791f', PSY: '#6250d6', SOC: '#1b9e77', SPI: '#c2410c', FAM: '#be185d',
  MUS: '#7c3aed', ENV: '#3d7d28', CIV: '#3e6292', EMP: '#db2777', SPO: '#0e7490', CUL: '#a16207', UNI: '#0f5e63',
}

export function CategoryIcon({ id, icon, size = 20, framed = true }: { id?: string; icon?: string; size?: number; framed?: boolean }) {
  const Ico = ICONS[icon ?? CAT_ICON[id ?? ''] ?? 'globe'] ?? Globe
  const tint = CAT_TINT[id ?? ''] ?? '#0f5e63'
  if (!framed) return <Ico size={size} style={{ color: tint }} aria-hidden />
  return (
    <span className="inline-grid place-items-center rounded-xl shrink-0" style={{ width: size * 2, height: size * 2, background: `${tint}1f`, color: tint }}>
      <Ico size={size} aria-hidden />
    </span>
  )
}

// Level badge: colour + distinct shape + text, so status is never colour-alone.
const SHAPES: Record<string, typeof Circle> = {
  'Needs Attention': Triangle, Developing: Diamond, Balanced: Square, Good: Circle, Thriving: Star,
}
export function LevelBadge({ level, small }: { level?: string | null; small?: boolean }) {
  if (!level) return <span className="chip bg-surface2 text-muted">Not assessed</span>
  const S = SHAPES[level] ?? Minus
  const c = levelColor(level)
  return (
    <span className={clsx('chip border', small && 'text-[11px] px-2')} style={{ color: c, borderColor: c, background: 'transparent' }}>
      <S size={10} fill="currentColor" aria-hidden /> {level}
    </span>
  )
}

export function Delta({ value }: { value: number | null | undefined }) {
  if (value === null || value === undefined) return <span className="text-xs text-muted">no prior data</span>
  const up = value > 2, down = value < -2
  const Ico = up ? TrendingUp : down ? TrendingDown : Minus
  return (
    <span className={clsx('inline-flex items-center gap-1 text-xs font-semibold', up ? 'text-leaf' : down ? 'text-saffron' : 'text-muted')}>
      <Ico size={14} aria-hidden /> {value > 0 ? '+' : ''}{value.toFixed(0)} {up ? 'improved' : down ? 'lower' : 'steady'}
    </span>
  )
}

export function ProgressBar({ value, target, color }: { value: number | null; target?: number | null; color?: string }) {
  return (
    <div className="relative h-2 rounded-full bg-surface2" role="progressbar" aria-valuenow={value ?? undefined} aria-valuemin={0} aria-valuemax={100}>
      {value !== null && <div className="h-2 rounded-full" style={{ width: `${Math.max(2, value)}%`, background: color ?? 'rgb(var(--teal))' }} />}
      {target != null && <div className="absolute -top-1 h-4 w-0.5 bg-ink/60" style={{ left: `${target}%` }} title={`Target ${target}`} />}
    </div>
  )
}

export function ScoreRing({ value, level, size = 120, label }: { value: number | null; level?: string | null; size?: number; label?: string }) {
  const r = 44, c = 2 * Math.PI * r
  const pct = value ?? 0
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" role="img" aria-label={`${label ?? 'Score'} ${fmt(value)} of 100`}>
      <circle cx="50" cy="50" r={r} fill="none" stroke="rgb(var(--surface2))" strokeWidth="8" />
      {value !== null && (
        <circle cx="50" cy="50" r={r} fill="none" stroke={levelColor(level)} strokeWidth="8" strokeLinecap="round"
          strokeDasharray={`${(pct / 100) * c} ${c}`} transform="rotate(-90 50 50)" />
      )}
      <text x="50" y="50" textAnchor="middle" dominantBaseline="central" className="fill-ink font-display" fontSize="26" fontWeight="600">{fmt(value)}</text>
      {label && <text x="50" y="70" textAnchor="middle" className="fill-muted" fontSize="8">{label}</text>}
    </svg>
  )
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl sm:text-3xl font-semibold text-ink">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted max-w-2xl">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  )
}

export function Spinner({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 p-8 text-muted" role="status">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-teal border-t-transparent" /> {label}
    </div>
  )
}

export function ErrorNote({ msg }: { msg: string | null }) {
  if (!msg) return null
  return <div className="card border-[color:var(--lv-attention)] p-4 text-sm" style={{ color: 'var(--lv-attention)' }} role="alert">{msg}</div>
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="card p-8 text-center">
      <h3 className="text-lg font-semibold">{title}</h3>
      <div className="mt-2 text-sm text-muted">{children}</div>
    </div>
  )
}

export function Disclaimer({ children }: { children?: ReactNode }) {
  return (
    <p className="flex gap-2 text-xs text-muted">
      <Info size={14} className="shrink-0 mt-0.5" aria-hidden />
      <span>{children ?? 'Wellness scores are self-assessment indicators, not medical diagnoses or professional financial assessments.'}</span>
    </p>
  )
}

export function SafetyBanner({ safety }: { safety: { message: string; resources: { name: string; contact: string }[] } | null | undefined }) {
  if (!safety) return null
  return (
    <div className="card mb-6 border-2 p-5" style={{ borderColor: 'var(--lv-attention)' }} role="alert">
      <div className="flex gap-3">
        <AlertTriangle className="shrink-0" style={{ color: 'var(--lv-attention)' }} aria-hidden />
        <div>
          <p className="font-semibold">{safety.message}</p>
          <ul className="mt-3 space-y-2">
            {safety.resources.map((r) => (
              <li key={r.name} className="flex items-center gap-2 text-sm">
                <Phone size={14} aria-hidden /> <span>{r.name}</span>
                {r.contact && <a className="font-bold text-teal underline" href={`tel:${r.contact.split(' ')[0]}`}>{r.contact}</a>}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: ReactNode }) {
  return (
    <div className="card p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-1 font-display text-2xl font-semibold">{value}</div>
      {hint && <div className="mt-0.5 text-xs text-muted">{hint}</div>}
    </div>
  )
}

export const LevelLegend = () => (
  <div className="flex flex-wrap gap-2">{Object.keys(LEVELS).filter((l) => l !== 'Insufficient data').map((l) => <LevelBadge key={l} level={l} small />)}</div>
)
