import { useEffect, useState } from 'react'
import {
  Bar, BarChart, CartesianGrid, Line, LineChart, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart,
  ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { Table2, BarChart3 } from 'lucide-react'
import clsx from 'clsx'
import { fmt } from '../lib/levels'

/** Resolve CSS custom properties into concrete colours (re-read when the theme changes). */
export function useVars<T extends string>(names: T[]): Record<T, string> {
  const read = () => Object.fromEntries(names.map((n) => [n, getComputedStyle(document.documentElement).getPropertyValue(n).trim()])) as Record<T, string>
  const [v, setV] = useState(read)
  useEffect(() => {
    const update = () => setV(read())
    const mo = new MutationObserver(update)
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    mq.addEventListener('change', update)
    return () => { mo.disconnect(); mq.removeEventListener('change', update) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  return v
}

const rgb = (s: string) => (s.includes(' ') && !s.startsWith('#') ? `rgb(${s.split(' ').join(',')})` : s)

function TipBox({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl border border-line bg-surface px-3 py-2 text-xs shadow-card">
      <div className="mb-1 font-semibold text-ink">{label ?? payload[0]?.payload?.category}</div>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center gap-2 text-ink">
          <span className="inline-block h-2 w-2 rounded-full" style={{ background: p.stroke || p.fill }} />
          <span className="text-muted">{p.name}</span><span className="ml-auto font-semibold">{fmt(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

export type SeriesKey = 'baseline' | 'previous' | 'current' | 'target'
const SERIES: { key: SeriesKey; name: string; v: string; dash?: string }[] = [
  { key: 'current', name: 'Current quarter', v: '--s-current' },
  { key: 'target', name: 'Target', v: '--s-target', dash: '5 4' },
  { key: 'previous', name: 'Previous quarter', v: '--s-previous' },
  { key: 'baseline', name: 'Initial assessment', v: '--s-baseline', dash: '2 3' },
]

export function WellnessRadar({ data }: { data: any[] }) {
  const c = useVars(['--s-current', '--s-target', '--s-previous', '--s-baseline', '--grid', '--muted', '--ink'])
  const available = SERIES.filter((s) => data.some((d) => d[s.key] !== null && d[s.key] !== undefined))
  const [on, setOn] = useState<Record<string, boolean>>({ current: true, target: true, previous: true, baseline: false })
  const [table, setTable] = useState(false)
  const shown = available.filter((s) => on[s.key])
  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        {available.map((s) => (
          <button key={s.key} aria-pressed={!!on[s.key]} onClick={() => setOn({ ...on, [s.key]: !on[s.key] })}
            className={clsx('chip min-h-[32px] border', on[s.key] ? 'border-ink/30 text-ink' : 'border-line text-muted opacity-60')}>
            <svg width="18" height="8" aria-hidden><line x1="0" y1="4" x2="18" y2="4" stroke={c[s.v as keyof typeof c]} strokeWidth="2.5" strokeDasharray={s.dash} /></svg>
            {s.name}
          </button>
        ))}
        <button className="chip ml-auto min-h-[32px] border border-line text-muted" onClick={() => setTable(!table)} aria-pressed={table}>
          {table ? <BarChart3 size={13} /> : <Table2 size={13} />} {table ? 'Chart view' : 'Table view'}
        </button>
      </div>
      {table ? (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-line text-left text-xs uppercase text-muted"><th className="py-2">Dimension</th>{available.map((s) => <th key={s.key} className="px-2 text-right">{s.name}</th>)}</tr></thead>
            <tbody>{data.map((d) => <tr key={d.category_id} className="border-b border-line/60"><td className="py-1.5">{d.category}</td>{available.map((s) => <td key={s.key} className="px-2 text-right tabular-nums">{fmt(d[s.key])}</td>)}</tr>)}</tbody>
          </table>
        </div>
      ) : (
        <div className="h-[380px] sm:h-[440px]" role="img" aria-label="Radar chart of 14 wellness dimension scores">
          <ResponsiveContainer>
            <RadarChart data={data} outerRadius="72%" margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
              <PolarGrid stroke={c['--grid']} />
              <PolarAngleAxis dataKey="category" tick={{ fill: rgb(c['--ink']), fontSize: 11 }} />
              <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: rgb(c['--muted']), fontSize: 9 }} tickCount={6} axisLine={false} />
              {shown.map((s) => (
                <Radar key={s.key} name={s.name} dataKey={s.key} stroke={c[s.v as keyof typeof c]} strokeWidth={2} strokeDasharray={s.dash}
                  fill={c[s.v as keyof typeof c]} fillOpacity={s.key === 'current' ? 0.18 : 0} dot={s.key === 'current' ? { r: 3 } : false} isAnimationActive={false} />
              ))}
              <Tooltip content={<TipBox />} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

export function Sparkline({ data, dataKey, target }: { data: any[]; dataKey: string; target?: number }) {
  const c = useVars(['--s-current', '--s-target', '--grid', '--muted'])
  return (
    <div className="h-24">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 6, right: 6, bottom: 0, left: -28 }}>
          <CartesianGrid stroke={c['--grid']} strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="period" tick={{ fontSize: 9, fill: rgb(c['--muted']) }} tickLine={false} axisLine={false} />
          <YAxis domain={[0, 100]} ticks={[0, 50, 100]} tick={{ fontSize: 9, fill: rgb(c['--muted']) }} tickLine={false} axisLine={false} />
          {target != null && <ReferenceLine y={target} stroke={c['--s-target']} strokeDasharray="4 3" />}
          <Line dataKey={dataKey} name="Score" stroke={c['--s-current']} strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} connectNulls isAnimationActive={false} />
          <Tooltip content={<TipBox />} cursor={{ stroke: c['--grid'] }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export function OverallTrend({ data }: { data: any[] }) {
  const c = useVars(['--s-current', '--grid', '--muted'])
  return (
    <div className="h-56">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 10, right: 16, bottom: 0, left: -16 }}>
          <CartesianGrid stroke={c['--grid']} strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="period" tick={{ fontSize: 11, fill: rgb(c['--muted']) }} tickLine={false} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: rgb(c['--muted']) }} tickLine={false} axisLine={false} />
          <Line dataKey="overall" name="Overall indicator" stroke={c['--s-current']} strokeWidth={2} dot={{ r: 5 }} activeDot={{ r: 7 }} connectNulls isAnimationActive={false} />
          <Tooltip content={<TipBox />} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export function HabitBars({ data }: { data: any[] }) {
  const c = useVars(['--bar', '--grid', '--muted'])
  return (
    <div className="h-56">
      <ResponsiveContainer>
        <BarChart data={data.map((d) => ({ ...d, label: d.week.slice(5) }))} margin={{ top: 10, right: 8, bottom: 0, left: -24 }} barCategoryGap={2}>
          <CartesianGrid stroke={c['--grid']} strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 10, fill: rgb(c['--muted']) }} tickLine={false} />
          <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: rgb(c['--muted']) }} tickLine={false} axisLine={false} />
          <Bar dataKey="completions" name="Completions (week of)" fill={c['--bar']} radius={[4, 4, 0, 0]} isAnimationActive={false} />
          <Tooltip content={<TipBox />} cursor={{ fill: 'rgba(127,127,127,0.08)' }} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
