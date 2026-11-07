export const LEVELS: Record<string, { color: string; short: string }> = {
  'Needs Attention': { color: 'var(--lv-attention)', short: 'Attention' },
  Developing: { color: 'var(--lv-developing)', short: 'Developing' },
  Balanced: { color: 'var(--lv-balanced)', short: 'Balanced' },
  Good: { color: 'var(--lv-good)', short: 'Good' },
  Thriving: { color: 'var(--lv-thriving)', short: 'Thriving' },
  'Insufficient data': { color: 'rgb(var(--muted))', short: 'No data' },
}
export const levelColor = (l?: string | null) => (l && LEVELS[l]?.color) || 'rgb(var(--muted))'
export const fmt = (v: number | null | undefined, d = 0) => (v === null || v === undefined ? '—' : v.toFixed(d))
