/**
 * SWASTI emblem: a unity ring holding 14 interconnected nodes (the 14 wellness
 * dimensions), a stylised lotus (balance and growth) and a central diya-inspired
 * light (knowledge and inner awareness). Deliberately non-religious and minimal.
 */
export function Emblem({ size = 40, mono = false }: { size?: number; mono?: boolean }) {
  const nodes = Array.from({ length: 14 }, (_, i) => {
    const a = (i / 14) * Math.PI * 2 - Math.PI / 2
    return [50 + 41 * Math.cos(a), 50 + 41 * Math.sin(a)]
  })
  const teal = mono ? 'currentColor' : '#B4530A'
  const leaf = mono ? 'currentColor' : '#F0A04B'
  const saffron = mono ? 'currentColor' : '#E07A1F'
  const petal = 'M50 70 C41 60 41 46 50 34 C59 46 59 60 50 70 Z'
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" role="img" aria-label="SWASTI emblem">
      <circle cx="50" cy="50" r="47" fill="none" stroke={teal} strokeWidth="3" />
      <circle cx="50" cy="50" r="41" fill="none" stroke={teal} strokeWidth="0.8" strokeOpacity="0.5" />
      {nodes.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="2.6" fill={i % 2 ? leaf : teal} />
      ))}
      <g opacity="0.95">
        <path d={petal} fill={leaf} fillOpacity="0.55" transform="rotate(-62 50 70)" />
        <path d={petal} fill={leaf} fillOpacity="0.55" transform="rotate(62 50 70)" />
        <path d={petal} fill={teal} fillOpacity="0.75" transform="rotate(-31 50 70)" />
        <path d={petal} fill={teal} fillOpacity="0.75" transform="rotate(31 50 70)" />
        <path d={petal} fill={teal} />
      </g>
      <path d="M36 70 Q50 81 64 70 Z" fill={saffron} />
      <path d="M50 41 C54.5 47 54.5 53 50 56 C45.5 53 45.5 47 50 41 Z" fill={mono ? 'none' : '#FFE7C2'} stroke={saffron} strokeWidth="1.6" />
      <circle cx="50" cy="51" r="1.8" fill={saffron} />
    </svg>
  )
}

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <Emblem size={compact ? 32 : 40} />
      <div className="leading-tight">
        <div className="font-display text-lg font-semibold tracking-[0.18em] text-teal">SWASTI</div>
        {!compact && <div className="text-[10px] text-muted tracking-wide">360° Human Wellness &amp; Life Balance</div>}
      </div>
    </div>
  )
}
